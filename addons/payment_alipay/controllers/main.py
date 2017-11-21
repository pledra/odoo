# -*- coding: utf-8 -*-

import logging
import pprint
import requests

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AlipayController(http.Controller):
    _notify_url = '/payment/alipay/notify'
    _return_url = '/payment/alipay/return'

    def aliapay_validate_data(self, **post):
        res = False
        if post['trade_status'] in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            _logger.info('Alipay: validated data')
            post['reference'] = request.env['payment.transaction'].sudo().search([('out_trade_no', '=', post['out_trade_no'])]).reference
            res = request.env['payment.transaction'].sudo().form_feedback(post, 'alipay')
        elif post['trade_status'] == 'TRADE_CLOSED':
            _logger.warning('Alipay: payment refunded to user and closed the transaction')
        else:
            _logger.warning('Alipay: unrecognized alipay answer, received %s instead of TRADE_FINISHED/TRADE_SUCCESS and TRADE_CLOSED' % (post['trade_status']))
        return res

    @http.route('/payment/alipay/return', type='http', auth="public", website=True)
    def alipay_return(self, **post):
        """ Alipay return """
        _logger.info('Beginning Alipay form_feedback with post data %s', pprint.pformat(post))  # debug
        self.aliapay_validate_data(**post)
        return request.redirect('/shop/payment/validate')

    @http.route('/payment/alipay/notify', type='http', auth='public')
    def alipay_notify(self, **post):
        """ Alipay Notify """
        _logger.info('Beginning Alipay Notify form_feedback with post data %s', pprint.pformat(post))  # debug
        alipay = request.env['payment.acquirer'].sudo().search([('provider', '=', 'alipay')])
        val = {
            'service': 'notify_verify',
            'partner': alipay.alipay_partner_id,
            'notify_id': post['notify_id']
        }
        sign = alipay.build_sign(val)
        val.update({
            'sign': sign,
            'sign_type': 'MD5'
        })
        urequest = requests.post(alipay._get_alipay_urls(alipay.environment), val)
        urequest.raise_for_status()
        resp = urequest.text
        if resp:
            try:
                _logger.info("success")  # do not modify or delete
            except ValidationError:
                _logger.exception('Unable to validate the Alipay payment')
            return 'success'
        return ""
