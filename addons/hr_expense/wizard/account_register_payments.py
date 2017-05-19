# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import url_encode
from odoo import api, models, _


class AccountRegisterPayments(models.TransientModel):
    _inherit = "account.register.payments"

    def _update_payment_vals(self, vals):
        if self._context.get('active_model') != 'hr.expense.sheet':
            return vals
        active_ids = self._context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)
        partner = expense_sheet.address_id or expense_sheet.employee_id.address_home_id
        vals.update(
            partner_type='supplier',
            payment_type='outbound',
            amount=abs(expense_sheet.total_amount),
            currency_id=expense_sheet.currency_id.id,
            partner_id=partner.id
        )
        return vals

    @api.model
    def default_get(self, fields):
        vals = super(AccountRegisterPayments, self).default_get(fields)
        return self._update_payment_vals(vals)

    @api.multi
    def _prepare_payment_vals(self, invoices):
        vals = super(AccountRegisterPayments, self)._prepare_payment_vals(invoices)
        return self._update_payment_vals(vals)

    def _create_payments(self):
        payment = super(AccountRegisterPayments, self)._create_payments()
        if self._context.get('active_model') != 'hr.expense.sheet':
            return payment
        active_ids = self._context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)

        # Log the payment in the chatter
        msg = _("A payment of %s %s with the reference <a href='/mail/view?%s'>%s</a> related to your expense <i>%s</i> has been made.")
        body = (msg % (payment.amount, payment.currency_id.symbol, url_encode({'model': 'account.payment', 'res_id': payment.id}), payment.name, expense_sheet.name))
        expense_sheet.message_post(body=body)

        # Reconcile the payment and the expense, i.e. lookup on the payable account move lines
        account_move_lines_to_reconcile = self.env['account.move.line']
        for line in payment.move_line_ids + expense_sheet.account_move_id.line_ids:
            if line.account_id.internal_type == 'payable':
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.reconcile()
        return payment

    @api.multi
    def create_payments(self):
        res = super(AccountRegisterPayments, self).create_payments()
        if self._context.get('active_model') != 'hr.expense.sheet':
            return res
        return {'type': 'ir.actions.act_window_close'}
