from passlib.context import CryptContext

from odoo import api, models, fields
from odoo.exceptions import AccessDenied

import logging

_logger = logging.getLogger(__name__)

CRYPT_CONTEXT = CryptContext(
    # kdf which can be verified by the context. The default encryption kdf is
    # the first of the list
    ['pbkdf2_sha512', 'md5_crypt', 'plaintext'],
    # deprecated algorithms are still verified as usual, but ``needs_update``
    # will indicate that the stored hash should be replaced by a more recent
    # algorithm. Passlib 1.6 supports an `auto` value which deprecates any
    # algorithm but the default, but Ubuntu LTS only provides 1.5 so far.
    deprecated=['md5_crypt', 'plaintext'],
)


class ResUsers(models.Model):
    _inherit = 'res.users'

    auth_token_ids = fields.One2many('auth.token', 'user_id', string='Authentication Tokens')

    @api.model
    def check_credentials(self, password):
        """
        Authenticate using a token.

        This override bypasses the ORM to check the hash of the provided password against the
        hash stored in an 'unaccessible' field. If the initial token was hashed using a deprecated
        hash function, the hash is updated. This authentication also logs the last connection date
        on the token for traceability purposes.
        """
        try:
            return super(ResUsers, self).check_credentials(password)
        except AccessDenied:
            now = fields.Datetime.now()
            query = """
            SELECT id, hash FROM auth_token WHERE
            user_id = %s AND
            valid_limit > %s;
            """
            self.env.cr.execute(query, (self.env.uid, now))
            rows = self.env.cr.dictfetchall()
            valid_pass = False
            for row in rows:
                valid_pass, replacement = CRYPT_CONTEXT.verify_and_update(password, row['hash'])
                token = self.env['auth.token'].sudo().browse(row['id'])
                if replacement is not None:
                    token._set_token(replacement)
                if valid_pass:
                    token.write({
                        'connection_date': fields.Datetime.now(),
                    })
                    break
            if not valid_pass:
                raise
            _logger.info('auth_token: connection as %s successful using token with id %s' % (self.env.user.login, row['id']))
