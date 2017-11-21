# coding: utf-8

import logging

from werkzeug import urls
from hashlib import md5

from odoo import api, fields, models, _
from odoo.addons.payment_alipay.controllers.main import AlipayController
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.http import request
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


class AcquirerAlipay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('alipay', 'Alipay')])
    alipay_payment_method = fields.Selection([
        ('standard_checkout', 'Standard Checkout'),
        ('express_checkout', 'Express Checkout'),
    ], 'Payment Method', default='standard_checkout')
    alipay_partner_id = fields.Char('Alipay Partner ID', required_if_provider='alipay', groups='base.group_user')
    alipay_partner_key = fields.Char('Alipay Partner Key', groups='base.group_user', required_if_provider='alipay')
    alipay_seller_email = fields.Char('Alipay seller Email', required_if_provider='alipay', groups='base.group_user')

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * md5 decryption : support saving payment data by md5 decryption
        """
        res = super(AcquirerAlipay, self)._get_feature_support()
        res['fees'].append('alipay')
        return res

    @api.model
    def _get_alipay_urls(self, environment):
        """ Alipay URLS """
        if environment == 'prod':
            return 'https://mapi.alipay.com/gateway.do'
        else:
            return 'https://openapi.alipaydev.com/gateway.do'

    @api.multi
    def alipay_compute_fees(self, amount, currency_id, country_id):
        """ Compute alipay fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        if not self.fees_active:
            return 0.0
        country = self.env['res.country'].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    @api.multi
    def get_trade_no(self):
        date = fields.datetime.now().strftime('%Y%m%d%H%M%S')
        return "odoo" + date

    @api.multi
    def build_sign(self, val):
        data_string = '&'.join(["{}={}".format(k, v) for k, v in sorted(val.items()) if k not in ['sign', 'sign_type', 'reference']]) + self.alipay_partner_key
        return md5(data_string.encode('utf-8')).hexdigest()

    @api.multi
    def alipay_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        alipay_tx_values = dict()

        product_name = ""
        product_desc = ""
        if request:
            for rec in self.env['sale.order'].browse(request.session.sale_order_id).order_line:
                product_name += rec.product_id.name + ", "
                product_desc += rec.product_id.description_sale.replace('\n', ',') + ", "

        alipay_tx_values.update({
            '_input_charset': 'utf-8',
            'body': (product_desc[:397] + '...') if len(product_desc) > 397 else product_desc[:-2],  # support only 400 char (except special char) in body (product description)
            'notify_url': urls.url_join(base_url, AlipayController._notify_url),
            'out_trade_no': self.get_trade_no(),
            'partner': self.alipay_partner_id,
            'return_url': urls.url_join(base_url, AlipayController._return_url),
            'subject': product_name[:-2],
            'total_fee': values['amount'] + values['fees'],
        })
        self.env['payment.transaction'].search([('reference', '=', values['reference'])]).write({
            'out_trade_no': alipay_tx_values['out_trade_no']
            })
        if self.alipay_payment_method == 'standard_checkout':
            alipay_tx_values.update({
                'product_code': 'NEW_OVERSEAS_SELLER',
                'service': 'create_forex_trade',
                'currency': values['currency'].name,
            })
        else:
            alipay_tx_values.update({
                'payment_type': 1,
                'seller_email': self.alipay_seller_email,
                'service': 'create_direct_pay_by_user'
                })
        sign = self.build_sign(alipay_tx_values)

        alipay_tx_values.update({
            'sign_type': 'MD5',
            'sign': sign,
        })

        values.update(alipay_tx_values)
        return values

    @api.multi
    def alipay_get_form_action_url(self):
        return self._get_alipay_urls(self.environment)


class TxAlipay(models.Model):
    _inherit = 'payment.transaction'

    out_trade_no = fields.Char('Trade Number', readonly=True)
    provider = fields.Selection(related='acquirer_id.provider')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _alipay_form_get_tx_from_data(self, data):
        reference, txn_id, sign = data.get('reference'), data.get('trade_no'), data.get('sign')
        if not reference or not txn_id:
            error_msg = _('Alipay: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Alipay: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # verify sign
        sign_check = txs.acquirer_id.build_sign(data)
        if sign != sign_check:
            error_msg = _('Alipay: invalid sign, received %s, computed %s, for data %s') % (sign, sign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return txs

    @api.multi
    def _alipay_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        # check what is buyed
        if float_compare(float(data.get('total_fee', '0.0')), (self.amount + self.fees), 2) != 0:
            invalid_parameters.append(('total_fee', data.get('total_fee'), '%.2f' % self.amount))  # mc_gross is amount + fees
        if self.acquirer_id.alipay_payment_method == 'standard_checkout':
            if data.get('currency') != self.currency_id.name:
                invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))
        else:
            if data.get('seller_email') != self.acquirer_id.alipay_seller_email:
                invalid_parameters.append(('seller_email', data.get('seller_email'), self.acquirer_id.alipay_seller_email))
        return invalid_parameters

    @api.multi
    def _alipay_form_validate(self, data):
        status = data.get('trade_status')
        res = {
            'acquirer_reference': data.get('trade_no'),
        }
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            _logger.info('Validated Alipay payment for tx %s: set as done' % (self.reference))
            date_validate = fields.Datetime.now()
            res.update(state='done', date_validate=date_validate)
            return self.write(res)
        elif status == 'TRADE_CLOSED':
            _logger.info('Received notification for Alipay payment %s: set as Canceled' % (self.reference))
            res.update(state='cancel', state_message=data.get('close_reason', ''))
            return self.write(res)
        else:
            error = 'Received unrecognized status for Alipay payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state='error', state_message=error)
            return self.write(res)
