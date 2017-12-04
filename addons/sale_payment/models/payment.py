# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
# from odoo.tools import float_compare
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.multi
    def post(self):
        '''Sales orders are sent automatically upon the transaction is posted.
        if the option <??????> is enabled, an invoice is created for each sales orders and they are linked
        to the account.payment using the inherits.
        If not, the sales orders are paid by creating some account.move.lines.
        '''
        #TODO
        for trans in self.filtered(lambda t: t.sale_order_ids):
            sale_order_ids = trans.sale_order_ids
            sale_order_ids._force_lines_to_invoice_policy_order()
            sale_order_company = sale_order_ids[0].company_id
            ctx_company = {'company_id': sale_order_company.id, 'force_company': sale_order_company.id}
            invoice_ids = sale_order_ids.with_context(**ctx_company).action_invoice_create()
            trans.invoice_ids = [(6, 0, invoice_ids)]
        return super(PaymentTransaction, self).post()

    @api.multi
    def mark_as_pending(self):
        super(PaymentTransaction, self).mark_as_pending()
        for trans in self:
            sale_order_ids = trans.sale_order_ids
            sale_order_ids.filtered(lambda so: so.state == 'draft').action_confirm()
            sale_order_ids.filtered(lambda so: so.state == 'sent').force_quotation_send()

    # --------------------------------------------------
    # Tools for payment
    # --------------------------------------------------

    def confirm_sale_token(self):
        """ Confirm a transaction token and call SO confirmation if it is a success.
        :return: True if success; error string otherwise """
        self.ensure_one()
        if self.payment_token_id:
            try:
                s2s_result = self.s2s_do_transaction()
            except Exception as e:
                _logger.warning(
                    _("<%s> transaction (%s) failed: <%s>") %
                    (self.acquirer_id.provider, self.id, str(e)))
                return 'pay_sale_tx_fail'

            if not s2s_result or not self.pending or\
                (self.acquirer_id.capture_manually and not self.authorized or self.state == 'draft'):
                _logger.warning(
                    _("<%s> transaction (%s) invalid state: %s") %
                    (self.acquirer_id.provider, self.id, self.state_message))
                return 'pay_sale_tx_state'
        return 'pay_sale_tx_token'

    def _check_or_create_sale_tx(self, order, acquirer, payment_token=None, tx_type='form', add_tx_values=None, reset_draft=True):
        tx = self
        if not tx:
            tx = self.search([('reference', '=', order.name)], limit=1)

        if tx.state == 'cancelled':  # filter incorrect states
            tx = False
        if (tx and tx.acquirer_id != acquirer) or (tx and order not in tx.sale_order_ids):  # filter unmatching
            tx = False
        if tx and payment_token and tx.payment_token_id and payment_token != tx.payment_token_id:  # new or distinct token
            tx = False

        # still draft tx, no more info -> rewrite on tx or create a new one depending on parameter
        if tx and tx.state == 'draft':
            tx = False

        if not tx:
            if not add_tx_values:
                add_tx_values = {}
            add_tx_values['type'] = tx_type
            if payment_token and payment_token.sudo().partner_id == order.partner_id:
                add_tx_values['payment_token_id'] = payment_token.id
            tx = order.create_payment_transaction(
                acquirer, payment_token=payment_token, additional_values=add_tx_values)

        # update quotation
        order.write({
            'payment_tx_id': tx.id,
        })

        return tx

    def render_sale_button(self, order, return_url, submit_txt=None, render_values=None):
        values = {
            'return_url': return_url,
            'partner_id': order.partner_shipping_id.id or order.partner_invoice_id.id,
            'billing_partner_id': order.partner_invoice_id.id,
        }
        if render_values:
            values.update(render_values)
        return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            self.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values=values,
        )
