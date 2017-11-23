# -*- coding: utf-8 -*-

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_alipay.controllers.main import AlipayController
from werkzeug import urls

from odoo.tools import mute_logger

from lxml import objectify


class AlipayCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(AlipayCommon, self).setUp()

        self.alipay = self.env.ref('payment.payment_acquirer_alipay')

        # some CC
        self.amex = (('378282246310005', '123'), ('371449635398431', '123'))
        self.amex_corporate = (('378734493671000', '123'))
        self.autralian_bankcard = (('5610591081018250', '123'))
        self.dinersclub = (('30569309025904', '123'), ('38520000023237', '123'))
        self.discover = (('6011111111111117', '123'), ('6011000990139424', '123'))
        self.jcb = (('3530111333300000', '123'), ('3566002020360505', '123'))
        self.mastercard = (('5555555555554444', '123'), ('5105105105105100', '123'))
        self.visa = (('4111111111111111', '123'), ('4012888888881881', '123'), ('4222222222222', '123'))
        self.dankord_pbs = (('76009244561', '123'), ('5019717010103742', '123'))
        self.switch_polo = (('6331101999990016', '123'))


class AlipayForm(AlipayCommon):

    def test_10_alipay_form_render(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # be sure not to do stupid things
        self.alipay.write({'alipay_partner_id': 'dummy', 'alipay_partner_key': 'dummy', 'alipay_seller_email': 'dummy', 'fees_active': False})
        self.assertEqual(self.alipay.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        # render the button
        res = self.alipay.render(
            'test_ref0', 0.01, self.currency_euro.id,
            values=self.buyer_values)

        form_values = {
            '_input_charset': 'utf-8',
            'body': '',
            'notify_url': urls.url_join(base_url, AlipayController._notify_url),
            'out_trade_no': self.alipay.get_trade_no(),
            'partner': self.alipay.alipay_partner_id,
            'return_url': urls.url_join(base_url, AlipayController._return_url),
            'subject': '',
            'total_fee': '0.01',
        }

        if self.alipay.alipay_payment_method == 'standard_checkout':
            form_values.update({
                'service': 'create_forex_trade',
                'currency': 'EUR',
                'product_code': 'NEW_OVERSEAS_SELLER',
            })
        else:
            form_values.update({
                'payment_type': '1',
                'seller_email': self.alipay.alipay_seller_email,
                'service': 'create_direct_pay_by_user'
                })
        sign = self.alipay.build_sign(form_values)

        form_values.update({
            'sign': sign,
            'sign_type': 'MD5'
            })
        # check form result
        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(len(data_set), 1, 'Alipay: Found %d "data_set" input instead of 1' % len(data_set))
        self.assertEqual(data_set[0].get('data-action-url'), 'https://openapi.alipaydev.com/gateway.do', 'alipay: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit', 'data_set', 'sign']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'alipay: wrong value for input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    def test_11_alipay_form_with_fees(self):
        # be sure not to do stupid things
        self.assertEqual(self.alipay.environment, 'test', 'test without test environment')

        # update acquirer: compute fees
        self.alipay.write({
            'fees_active': True,
            'fees_dom_fixed': 1.0,
            'fees_dom_var': 0.35,
            'fees_int_fixed': 1.5,
            'fees_int_var': 0.50,
        })

        # render the button
        res = self.alipay.render(
            'test_ref0', 12.50, self.currency_euro.id,
            values=self.buyer_values)

        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(len(data_set), 1, 'alipay: Found %d "data_set" input instead of 1' % len(data_set))
        self.assertEqual(data_set[0].get('data-action-url'), 'https://openapi.alipaydev.com/gateway.do', 'alipay: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['total_fee']:
                self.assertEqual(form_input.get('value'), '14.07', 'alipay: wrong computed fees')  # total amount = amount + fees

    @mute_logger('odoo.addons.payment_alipay.models.payment', 'ValidationError')
    def test_20_alipay_form_management(self):
        # be sure not to do stupid things
        self.assertEqual(self.alipay.environment, 'test', 'test without test environment')
        self.alipay.write({'alipay_partner_id': 'dummy', 'alipay_partner_key': 'dummy', 'alipay_seller_email': 'dummy', 'fees_active': False})

        # typical data posted by alipay after client has successfully paid
        alipay_post_data = {
            'trade_no': '2017112321001003690200384552',
            'reference': 'test_ref_2',
            'total_fee': 1.95,
            'currency': 'EUR',
            'trade_status': 'TRADE_CLOSED',
        }

        if self.alipay.alipay_payment_method == 'express_checkout':
            alipay_post_data.update({
                'seller_email': self.alipay.alipay_seller_email,
            })

        alipay_post_data['sign'] = self.alipay.build_sign(alipay_post_data)
        # should raise error about unknown tx
        with self.assertRaises(ValidationError):

            self.env['payment.transaction'].form_feedback(alipay_post_data, 'alipay')

        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.alipay.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_2',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # validate it
        tx.form_feedback(alipay_post_data, 'alipay')
        # check
        self.assertEqual(tx.state, 'cancel', 'alipay: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, '2017112321001003690200384552', 'alipay: wrong txn_id after receiving a valid pending notification')

        # update tx
        tx.write({
            'state': 'done',
            'acquirer_reference': False})

        # update notification from alipay
        if self.alipay.alipay_payment_method == 'standard_checkout':
            alipay_post_data['trade_status'] = 'TRADE_FINISHED'
        else:
            alipay_post_data['trade_status'] = 'TRADE_SUCCESS'
        alipay_post_data['sign'] = self.alipay.build_sign(alipay_post_data)
        # validate it
        tx.form_feedback(alipay_post_data, 'alipay')
        # check
        self.assertEqual(tx.state, 'done', 'alipay: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, '2017112321001003690200384552', 'alipay: wrong txn_id after receiving a valid pending notification')
