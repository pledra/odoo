# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountRegisterPayments(models.TransientModel):
    _inherit = "account.register.payments"

    check_amount_in_words = fields.Char(string="Amount in Words")

    @api.onchange('amount')
    def _onchange_amount(self):
        if hasattr(super(AccountRegisterPayments, self), '_onchange_amount'):
            super(AccountRegisterPayments, self)._onchange_amount()
        self.check_amount_in_words = self.currency_id.amount_to_text(self.amount)

    def _prepare_payment_vals(self, invoices):
        res = super(AccountRegisterPayments, self)._prepare_payment_vals(invoices)
        if self.payment_method_id == self.env.ref('account_check_printing.account_payment_method_check'):
            res.update({
                'check_amount_in_words': self.check_amount_in_words,
            })
        return res


class AccountPayment(models.Model):
    _inherit = "account.payment"

    check_amount_in_words = fields.Char(string="Amount in Words")
    check_manual_sequencing = fields.Boolean(related='journal_id.check_manual_sequencing')
    check_number = fields.Integer(string="Check Number", readonly=True, copy=False,
        help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
             "or if the current numbering is wrong, you can change it in the journal configuration page.")

    @api.onchange('amount','currency_id')
    def _onchange_amount(self):
        res = super(AccountPayment, self)._onchange_amount()
        self.check_amount_in_words = self.currency_id.amount_to_text(self.amount)
        return res

    def _check_communication(self, payment_method_id, communication):
        super(AccountPayment, self)._check_communication(payment_method_id, communication)
        if payment_method_id == self.env.ref('account_check_printing.account_payment_method_check').id:
            if not communication:
                return
            if len(communication) > 60:
                raise ValidationError(_("A check memo cannot exceed 60 characters."))

    @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        for payment in self.filtered(lambda r: r.payment_method_id == payment_method_check and r.check_manual_sequencing):
            sequence = payment.journal_id.check_sequence_id
            payment.check_number = sequence.next_by_id()
        return res

    @api.multi
    def print_checks(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        # Since this method can be called via a client_action_multi, we need to make sure the received records are what we expect
        self = self.filtered(lambda r: r.payment_method_id.code == 'check_printing' and r.state != 'reconciled')

        if len(self) == 0:
            raise UserError(_("Payments to print as a checks must have 'Check' selected as payment method and "
                              "not have already been reconciled"))
        if any(payment.journal_id != self[0].journal_id for payment in self):
            raise UserError(_("In order to print multiple checks at once, they must belong to the same bank journal."))

        if not self[0].journal_id.check_manual_sequencing:
            # The wizard asks for the number printed on the first pre-printed check
            # so payments are attributed the number of the check the'll be printed on.
            last_printed_check = self.search([
                ('journal_id', '=', self[0].journal_id.id),
                ('check_number', '!=', 0)], order="check_number desc", limit=1)
            next_check_number = last_printed_check and last_printed_check.check_number + 1 or 1
            return {
                'name': _('Print Pre-numbered Checks'),
                'type': 'ir.actions.act_window',
                'res_model': 'print.prenumbered.checks',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'payment_ids': self.ids,
                    'default_next_check_number': next_check_number,
                }
            }
        else:
            self.filtered(lambda r: r.state == 'draft').post()
            return self.do_print_checks()

    @api.multi
    def unmark_sent(self):
        self.write({'state': 'posted'})

    @api.multi
    def do_print_checks(self):
        """ This method is a hook for l10n_xx_check_printing modules to implement actual check printing capabilities """
        raise UserError(_("There is no check layout configured.\nMake sure the proper check printing module is installed"
                          " and its configuration (in company settings > 'Configuration' tab) is correct."))
