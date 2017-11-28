from datetime import datetime
from dateutil.relativedelta import relativedelta as delta

from odoo import models, fields
from odoo.exceptions import UserError


class AuthTokenWizard(models.TransientModel):
    _name = 'auth.token.wizard'
    _description = 'Authentication Token Wizard'

    def _default_user(self):
        if self._context.get('active_model') == 'res.users':
            return self._context.get('active_id', self.env.uid)
        return self.env.uid

    user_id = fields.Many2one('res.users', string='User to Impersonate', required=True, default=_default_user, domain="[('share', '=', False)]")
    validity = fields.Selection([('hour', '1 Hour'), ('4hours', '4 Hours'),
                                 ('24hours', '24 Hours'), ('custom', 'Custom')],
                                string='Validity', required=True, default='4hours')
    valid_limit = fields.Datetime(string='Validity Limit')
    comment = fields.Text(string='Comment')
    recipients = fields.Char(string='Recipients', help="Emails you wish to send this access code to. You can enter multiple emails divided by a semicolon (;)")

    def _compute_url(self, token):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '%s/auth_token/login?db=%s&login=%s&token=%s' % (base_url, self.env.cr.dbname, self.user_id.login, token)

    def create_token(self):
        if self.validity == 'hour':
            self.valid_limit = datetime.now() + delta(hours=1)
        if self.validity == '4hours':
            self.valid_limit = datetime.now() + delta(hours=4)
        if self.validity == '24hours':
            self.valid_limit = datetime.now() + delta(hours=24)
        (auth_token, token) = self.env['auth.token'].create_and_set_token({
            'user_id': self.user_id.id,
            'valid_limit': self.valid_limit,
            'comment': self.comment,
        })
        user = auth_token.user_id
        mail_template = self.env['ir.model.data'].xmlid_to_object('auth_token.token_invite', raise_if_not_found=False)
        url = self._compute_url(token)
        mail = False
        if self.recipients and mail_template:
            email_context = {
                'url': url,
                'limit_validity': auth_token.valid_limit,
                'email_to': self.recipients,
                'comment': self.comment,
            }
            try:
                mail = mail_template.with_context(email_context).send_mail(auth_token.id)
            except UserError:
                mail = False
        return {
            'type': 'ir.actions.client',
            'tag': 'auth_token.wizard',
            'target': 'new',
            'url': url,
            'limit_validity': auth_token.valid_limit,
            'user': {'name': user.name, 'login': user.login},
            'email_success': bool(mail_template and mail),
            'recipients': self.recipients,
            'context': self.env.context,
        }
