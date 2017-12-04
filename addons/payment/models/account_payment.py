# coding: utf-8

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_transaction_ids = fields.One2many('payment.transaction', 'payment_id', string='Transactions')
    payment_transaction_id = fields.Many2one('payment.transaction', string='Transaction',
                                             compute='_compute_payment_transaction_id')
    payment_transaction_authorized = fields.Boolean(related='payment_transaction_id.authorized')

    @api.depends('payment_transaction_ids')
    def _compute_payment_transaction_id(self):
        for pay in self:
            pay.payment_transaction_id = pay.payment_transaction_ids and pay.payment_transaction_ids[0] or False

    @api.multi
    def _check_payment_transaction_id(self):
        if any(not p.payment_transaction_ids for p in self):
            raise ValidationError(_('Only payments linked to some transactions can be proceeded.'))

    @api.multi
    def action_capture(self):
        self._check_payment_transaction_id()
        payment_transaction_ids = self.mapped('payment_transaction_ids')
        if any(not t.authorized for t in payment_transaction_ids):
            raise ValidationError(_('Only transactions having the Authorized status can be captured.'))
        payment_transaction_ids.s2s_capture_transaction()

    @api.multi
    def action_void(self):
        self._check_payment_transaction_id()
        payment_transaction_ids = self.mapped('payment_transaction_ids')
        if any(not t.authorized for t in payment_transaction_ids):
            raise ValidationError(_('Only transactions having the Authorized status can be voided.'))
        payment_transaction_ids.s2s_void_transaction()

    @api.constrains('payment_transaction_ids')
    def _check_only_one_transaction(self):
        for pay in self:
            if len(pay.payment_transaction_ids) > 1:
                raise UserError(_('Only one transaction per payment is allowed!'))
