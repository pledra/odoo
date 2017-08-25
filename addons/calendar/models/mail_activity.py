# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools, _


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('meeting', 'Meeting')])


class MailActivity(models.Model):
    _inherit = "mail.activity"

    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Meeting", ondelete='cascade')

    @api.multi
    def action_create_calendar_event(self):
        self.ensure_one()
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['context'] = {
            'activity_type_id': self.activity_type_id.id,
            'default_res_id': self.env.context.get('default_res_id'),
            'default_res_model': self.env.context.get('default_res_model'),
            'default_name': self.summary,
            'default_description': self.note and tools.html2plaintext(self.note) or '',
            'create_activity': True,
        }
        self.unlink()
        return action

    @api.multi
    def unlink(self):
        for activity in self.filtered('feedback'):
            feedback = tools.html2plaintext(activity.feedback)
            description = activity.calendar_event_id.description
            modify_feedback = (description or '') + "\n" + _("Feedback: ") + feedback
            activity.calendar_event_id.write({'description': modify_feedback})
        return super(MailActivity, self).unlink()
