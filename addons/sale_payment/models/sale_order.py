# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_ids = fields.Many2many('account.payment', 'sale_order_ids', string='Payments', readonly=True)
    payment_ids_nbr = fields.Integer(string='# of Payments', compute='_compute_payment_ids_nbr')
    payment_tx_id = fields.Many2one('payment.transaction', string='Last Transaction')
    payment_acquirer_id = fields.Many2one('payment.acquirer', related='payment_tx_id.acquirer_id')

    @api.depends('payment_ids')
    def _compute_payment_ids_nbr(self):
        for so in self:
            so.payment_ids_nbr = len(so.payment_ids)

    @api.multi
    def create_payment_transaction(self, acquirer, payment_token=None, save_token=None, additional_values=None):
        if not additional_values:
            additional_values = {}
        currency = self[0].pricelist_id.currency_id
        if any([so.pricelist_id.currency_id != currency for so in self]):
            raise UserError(_('A transaction can\'t be linked to sales orders having different currencies.'))
        partner = self[0].partner_id
        if any([so.partner_id != partner for so in self]):
            raise UserError(_('A transaction can\'t be linked to sales orders having different partners.'))
        if payment_token and payment_token.acquirer_id != acquirer:
            raise UserError(_('Invalid token found: token acquirer %s != %s') % (payment_token.acquirer_id.name, acquirer.name))
        if payment_token and payment_token.partner_id != partner:
            raise UserError(_('Invalid token found: token partner %s != %s') % (payment_token.partner.name, partner.name))

        amount = sum(self.mapped('amount_total'))
        payment_token_id = payment_token and payment_token.id or None
        transaction_type = additional_values.get('type', 'form_save' if save_token else 'form')

        transaction_vals = {
            'acquirer_id': acquirer.id,
            'type': transaction_type,
            'amount': amount,
            'currency_id': currency.id,
            'partner_id': partner.id,
            'partner_country_id': partner.country_id.id,
            'sale_order_ids': [(6, 0, self.ids)],
            'payment_token_id': payment_token_id,
        }
        transaction_vals.update(additional_values)

        transaction = self.env['payment.transaction'].create(transaction_vals)

        # track the last transaction: TODO check if necessary
        self.write({'payment_tx_id': transaction.id})

        return transaction

    @api.multi
    def action_view_payments(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
        }
        payment_ids = self.payment_ids
        if len(payment_ids) == 1:
            action.update({
                'res_id': payment_ids[0].id,
                'view_mode': 'form',
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payment_ids.ids)],
            })
        return action

    @api.multi
    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
