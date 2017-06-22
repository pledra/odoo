# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    so_line = fields.Many2one('sale.order.line', string='Sales Order Line')

    @api.model
    def create(self, values):
        result = super(AccountAnalyticLine, self).create(values)
        result._sale_update_delivered_qty()
        return result

    @api.multi
    def write(self, values):
        # get current so lines for which update qty wil be required
        sale_order_lines = self.env['sale.order.line']
        if 'so_line' in values:
            sale_order_lines = self.mapped('so_line')
        result = super(AccountAnalyticLine, self).write(values)
        # trigger the update of qty_delivered
        self._sale_update_delivered_qty(additionnal_so_lines=sale_order_lines)
        return result

    @api.multi
    def unlink(self):
        sale_order_lines = self.sudo().mapped('so_line')
        res = super(AccountAnalyticLine, self).unlink()
        self.env['account.analytic.line'].with_context(force_so_lines=sale_order_lines)._sale_update_delivered_qty(additionnal_so_lines=sale_order_lines)
        return res

    @api.multi
    def _sale_update_delivered_qty(self, additionnal_so_lines=None):
        """ Trigger the update of qty_delivered on related SO lines (of `self`) and other given
            additionnal lines.
        """
        sale_order_lines = self.filtered(lambda aal: aal.so_line).mapped('so_line')
        if additionnal_so_lines:
            sale_order_lines |= additionnal_so_lines

        # trigger the update of qty_delivered
        if sale_order_lines:
            sale_order_lines._compute_analytic()  # TODO JEM: change this method. Make something smart for the domain
