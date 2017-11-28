# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import api, fields, models
from odoo.addons.auth_token.models.res_users import CRYPT_CONTEXT


class AuthToken(models.Model):
    _name = 'auth.token'
    _description = 'Authentication Token'
    _order = 'valid_limit desc, id desc'

    user_id = fields.Many2one('res.users', string='Impersonated User', required=True, index=True)
    valid_limit = fields.Datetime(string='Validity Limit', required=True)
    connection_date = fields.Datetime(string='Last Used On')
    comment = fields.Text(string='Comment')
    expired = fields.Boolean(string='Expired', compute='_compute_expired')

    def _compute_expired(self):
        """Compute the expiration state of the token (expired if the date is in the past)."""
        now = fields.Datetime.now()
        for token in self:
            token.expired = token.valid_limit < now

    def init(self):
        """Add the hash column outside of the ORM's reach."""
        self.env.cr.execute('''
            DO $$
                BEGIN
                    ALTER TABLE auth_token ADD COLUMN hash varchar;
                EXCEPTION
                    WHEN duplicate_column THEN null;
              END;
            $$;
        ''')

    def _set_token(self, token):
        """Private function to set the hash column value without using the ORM."""
        self.ensure_one()
        encrypted = CRYPT_CONTEXT.encrypt(token)
        self.env.cr.execute('''
            UPDATE auth_token SET hash = %s WHERE id = %s
        ''', (encrypted, self.id))
        return token

    @api.model
    def _cron_gc_token(self):
        to_unlink = self.search([('valid_limit', '<', fields.Datetime.now())])
        to_unlink.unlink()
        return True

    @api.model
    def create_and_set_token(self, values):
        """
        Create the token and return it.

        Used to create the token and still be able to send a correct & useful link
        to connect using it.
        """
        auth_token = self.create(values)
        token = str(uuid.uuid4())
        auth_token._set_token(token)
        return (auth_token, token)
