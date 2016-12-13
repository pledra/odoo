# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class TemplatePreview(models.TransientModel):
    _inherit = "mail.template"
    _name = "email_template.preview"
    _description = "Email Template Preview"

    @api.model
    def _get_reference_model(self):
        template = self.env['mail.template'].browse(self._context.get('active_id'))
        return [(template.model_id.model, template.model_id.name)]

    @api.model
    def _get_default_preview(self):
        template = self.env['mail.template'].browse(self._context.get('active_id'))
        model = template.model_id.model
        record = self.env[model].search([], limit=1)
        if not record:
            raise UserError('There is no record on which to preview this template.')
        return "%s, %s" % (model, record.id)

    partner_ids = fields.Many2many('res.partner', string='Recipients')
    preview_record = fields.Reference(string="Preview on", selection=_get_reference_model,
                                      default=_get_default_preview)

    @api.onchange('preview_record')
    @api.multi
    def on_change_res_id(self):
        mail_values = {}
        if self.preview_record and self._context.get('template_id'):
            template = self.env['mail.template'].browse(self._context['template_id'])
            self.name = template.name
            mail_values = template.generate_email(self.preview_record.id)
        for field in ['email_from', 'email_to', 'email_cc', 'reply_to', 'subject', 'body_html', 'partner_to', 'partner_ids', 'attachment_ids']:
            setattr(self, field, mail_values.get(field, False))
