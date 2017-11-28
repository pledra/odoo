# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from urlparse import urlparse, parse_qs

from odoo.exceptions import AccessDenied
from odoo.tests import common
from odoo import fields


class AuthTokenTest(common.TransactionCase):

    def setUp(self):
        super(AuthTokenTest, self).setUp()
        group_user = self.env.ref('base.group_user')
        self.user = self.env['res.users'].create({
            'login': 'picard',
            'name': 'Jean-Luc Picard',
            'email': 'jl.picard@fed.uni',
            'new_password': 'picard-four-seven-alpha-tango',
            'groups_id': [(4, group_user.id, False)],
        })

    def test_01_auth_flow(self):
        """Check the normal authentication flow with a token."""
        wiz = self.env['auth.token.wizard'].create({
            'user_id': self.user.id,
            'validity': '4hours',
            'comment': 'test',
            'recipients': 'ale@odoo.com;dbo@odoo.com'
        })
        # let's assume a ~2 minute window for creation of the token, just in case of a very slow db
        now = datetime.now()
        validity_bounds = (now + timedelta(hours=4, seconds=-10), now + timedelta(hours=4, minutes=2))
        [validity_low, validity_high] = list(map(lambda d: fields.Datetime.to_string(d), validity_bounds))
        res = wiz.create_token()
        login_params = parse_qs(urlparse(res.get('url')).query)
        validity = res.get('limit_validity')
        email_ok = res.get('email_success')
        self.assertTrue(email_ok, 'remote_assistance: mail not sent to recipients')
        self.assertTrue(validity > validity_low)
        self.assertTrue(validity < validity_high)
        self.user.sudo(self.user.id).check_credentials(login_params['token'][0])

    def test_02_expired_auth(self):
        """Check that an expired token does not grant access."""
        now = datetime.now()
        expired_date = fields.Datetime.to_string(now + timedelta(minutes=-1))
        wiz = self.env['auth.token.wizard'].create({
            'user_id': self.user.id,
            'validity': 'custom',
            'valid_limit': expired_date,
            'comment': 'test',
            'recipients': 'ale@odoo.com;dbo@odoo.com'
        })
        res = wiz.create_token()
        login_params = parse_qs(urlparse(res.get('url')).query)
        with self.assertRaises(AccessDenied):
            self.user.check_credentials(login_params['token'][0])
        self.assertEqual(len(self.user.auth_token_ids.ids), 1)
        self.user.unlink_remote_tokens()
        self.assertEqual(len(self.user.auth_token_ids.ids), 0)

    def test_03_gc_token(self):
        """Check that tokens are garbage collected correctly."""
        now = datetime.now()
        expired_date = fields.Datetime.to_string(now + timedelta(minutes=-1))
        wiz = self.env['auth.token.wizard'].create({
            'user_id': self.user.id,
            'validity': 'custom',
            'valid_limit': expired_date,
            'comment': 'test',
            'recipients': 'ale@odoo.com;dbo@odoo.com'
        })
        wiz.create_token()
        self.assertEqual(len(self.user.auth_token_ids.ids), 1)
        self.env['auth.token']._cron_gc_token()
        self.assertEqual(len(self.user.auth_token_ids.ids), 0)
