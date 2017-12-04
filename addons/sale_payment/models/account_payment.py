# coding: utf-8

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    sale_order_ids = fields.Many2many('sale.order', string='Sales Orders', readonly=True)

    @api.multi
    def write(self, vals):
        # if vals.get('invoice_ids'):
        #     invoices = self.env['account.invoice'].resolve_2many_commands('invoice_ids', vals['invoice_ids'], fields=['id'])
        #     vals['sale_order_ids'] = [(6, 0, invoices.mapped('sale_order_ids').ids)]
        return super(AccountPayment, self).write(vals)
