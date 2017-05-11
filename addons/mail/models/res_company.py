# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import urlparse
import datetime

from odoo import api, fields, models, tools


class Company(models.Model):
    _inherit = 'res.company'

    mail_template_header = fields.Html()
    mail_template_footer = fields.Html()

    @api.model
    def get_default_fail_counter(self, fields):
        previous_date = datetime.datetime.now() - datetime.timedelta(days=30)
        return {
            'fail_counter': self.env['mail.mail'].sudo().search_count([('date', '>=', previous_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)), ('state', '=', 'exception')]),
        }

    @api.model
    def get_default_alias_domain(self, fields):
        alias_domain = self.env["ir.config_parameter"].get_param("mail.catchall.domain", default=None)
        if alias_domain is None:
            domain = self.env["ir.config_parameter"].get_param("web.base.url")
            try:
                alias_domain = urlparse.urlsplit(domain).netloc.split(':')[0]
            except Exception:
                pass
        return {'alias_domain': alias_domain or False}

    @api.multi
    def set_alias_domain(self):
        for record in self:
            self.env['ir.config_parameter'].set_param("mail.catchall.domain", record.alias_domain or '')
