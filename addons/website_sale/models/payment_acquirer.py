# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    def _get_custom_return_url(self):
        super(PaymentAcquirer, self)._get_custom_return_url()
        return '/shop/confirmation'

    def _get_custom_cancel_url(self):
        super(PaymentAcquirer, self)._get_custom_cancel_url()
        return '/shop/payment'
