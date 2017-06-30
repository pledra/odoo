# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):

    _inherit = "account.analytic.line"

    @api.model
    def create(self, values):
        result = super(AccountAnalyticLine, self).create(values)
        result._expense_set_sale_order_line()
        return result

    @api.multi
    def write(self, values):
        result = super(AccountAnalyticLine, self).write(values)
        self._expense_set_sale_order_line()
        return result

    @api.multi
    def _expense_get_invoice_price(self, order):
        self.ensure_one()
        if self.product_id.expense_policy == 'sales_price':
            return self.product_id.with_context(
                partner=order.partner_id.id,
                date_order=order.date_order,
                pricelist=order.pricelist_id.id,
                uom=self.product_uom_id.id
            ).price
        if self.unit_amount == 0.0:
            return 0.0

        # Prevent unnecessary currency conversion that could be impacted by exchange rate
        # fluctuations
        if self.currency_id and self.amount_currency and self.currency_id == order.currency_id:
            return abs(self.amount_currency / self.unit_amount)

        price_unit = abs(self.amount / self.unit_amount)
        currency_id = self.company_id.currency_id
        if currency_id and currency_id != order.currency_id:
            price_unit = currency_id.compute(price_unit, order.currency_id)
        return price_unit

    @api.multi
    def _expense_prepare_sale_order_line_values(self, order, price):
        self.ensure_one()
        last_so_line = self.env['sale.order.line'].search([('order_id', '=', order.id)], order='sequence desc', limit=1)
        last_sequence = last_so_line.sequence + 1 if last_so_line else 100

        fpos = order.fiscal_position_id or order.partner_id.property_account_position_id
        taxes = fpos.map_tax(self.product_id.taxes_id, self.product_id, order.partner_id)

        return {
            'order_id': order.id,
            'name': self.name,
            'sequence': last_sequence,
            'price_unit': price,
            'tax_id': [x.id for x in taxes],
            'discount': 0.0,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': 0.0,
            'qty_delivered': self.unit_amount,
        }

    @api.multi
    def _expense_set_sale_order_line(self):
        """ Automatically set the SO line on the analytic line, IF it concerns an expense. """
        for analytic_line in self.filtered(lambda aal: not aal.so_line and aal.product_id and aal.product_id.expense_policy != 'no'):
            # determine SO : first SO open linked to AA
            sale_order = self.env['sale.order'].search([('analytic_account_id', '=', analytic_line.account_id.id), ('state', '=', 'sale')], limit=1)
            if not sale_order:
                sale_order = self.env['sale.order'].search([('analytic_account_id', '=', analytic_line.account_id.id)], limit=1)
            if not sale_order:
                continue

            price = analytic_line._expense_get_invoice_price(sale_order)
            so_line = self.env['sale.order.line'].search([
                ('order_id', '=', sale_order.id),
                ('price_unit', '=', price),
                ('product_id', '=', self.product_id.id)], limit=1)

            if not so_line:
                # generate a new SO line
                if sale_order.state != 'sale':
                    raise UserError(_('The Sales Order %s linked to the Analytic Account must be validated before registering expenses.') % sale_order.name)
                so_line_values = analytic_line._expense_prepare_sale_order_line_values(sale_order, price)
                if so_line_values:
                    so_line = self.env['sale.order.line'].create(so_line_values)
                    so_line._compute_tax_id()

            if so_line:  # if so line found or created, then update AAL (this will trigger the recomputation of qty delivered on SO line)
                analytic_line.write({'so_line': so_line.id})
