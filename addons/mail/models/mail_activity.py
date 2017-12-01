# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo import api, exceptions, fields, models, _


class MailActivityType(models.Model):
    """ Activity Types are used to categorize activities. Each type is a different
    kind of activity e.g. call, mail, meeting. An activity can be generic i.e.
    available for all models using activities; or specific to a model in which
    case res_model_id field should be used. """
    _name = 'mail.activity.type'
    _description = 'Activity Type'
    _rec_name = 'name'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    summary = fields.Char('Summary', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    days = fields.Integer(
        '# Days', default=0,
        help='Number of days before executing the action. It allows to plan the action deadline.')
    icon = fields.Char('Icon', help="Font awesome icon e.g. fa-tasks")
    res_model_id = fields.Many2one(
        'ir.model', 'Model', index=True,
        help='Specify a model if the activity should be specific to a model'
             ' and not available when managing activities for other models.')
    next_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'activity_id', 'recommended_id',
        string='Recommended Next Activities')
    previous_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'recommended_id', 'activity_id',
        string='Preceding Activities')
    category = fields.Selection([
        ('default', 'Other')], default='default',
        string='Category',
        help='Categories may trigger specific behavior like opening calendar view')
    reminder_html = fields.Html('Reminder Text', help='Rendered using QWeb')


class MailActivity(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _name = 'mail.activity'
    _description = 'Activity'
    _order = 'date_deadline ASC'
    _rec_name = 'summary'

    @api.model
    def default_get(self, fields):
        res = super(MailActivity, self).default_get(fields)
        if not fields or 'res_model_id' in fields and res.get('res_model'):
            res['res_model_id'] = self.env['ir.model']._get(res['res_model']).id
        return res

    # owner
    res_id = fields.Integer('Related Document ID', index=True, required=True)
    res_model_id = fields.Many2one(
        'ir.model', 'Related Document Model',
        index=True, ondelete='cascade', required=True)
    res_model = fields.Char(
        'Related Document Model',
        index=True, related='res_model_id.model', store=True, readonly=True)
    res_name = fields.Char(
        'Document Name', compute='_compute_res_name', store=True,
        help="Display name of the related document.", readonly=True)
    # activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Activity',
        domain="['|', ('res_model_id', '=', False), ('res_model_id', '=', res_model_id)]")
    activity_category = fields.Selection(related='activity_type_id.category')
    icon = fields.Char('Icon', related='activity_type_id.icon')
    summary = fields.Char('Summary')
    note = fields.Html('Note')
    feedback = fields.Html('Feedback')
    date_deadline = fields.Date('Due Date', index=True, required=True, default=fields.Date.today)
    is_notified = fields.Boolean('Notified', help='Indicates whether a notification has been sent, either Inbox either email')
    # description
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True)
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], 'State',
        compute='_compute_state')
    recommended_activity_type_id = fields.Many2one('mail.activity.type', string="Recommended Activity Type")
    previous_activity_type_id = fields.Many2one('mail.activity.type', string='Previous Activity Type')
    has_recommended_activities = fields.Boolean(
        'Next activities available',
        compute='_compute_has_recommended_activities',
        help='Technical field for UX purpose')

    @api.multi
    @api.onchange('previous_activity_type_id')
    def _compute_has_recommended_activities(self):
        for record in self:
            record.has_recommended_activities = bool(record.previous_activity_type_id.next_type_ids)

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for activity in self:
            activity.res_name = self.env[activity.res_model].browse(activity.res_id).name_get()[0][1]

    @api.depends('date_deadline')
    def _compute_state(self):
        today = date.today()
        for record in self.filtered(lambda activity: activity.date_deadline):
            date_deadline = fields.Date.from_string(record.date_deadline)
            diff = (date_deadline - today)
            if diff.days == 0:
                record.state = 'today'
            elif diff.days < 0:
                record.state = 'overdue'
            else:
                record.state = 'planned'

    @api.onchange('activity_type_id')
    def _onchange_activity_type_id(self):
        if self.activity_type_id:
            self.summary = self.activity_type_id.summary
            self.date_deadline = (datetime.now() + timedelta(days=self.activity_type_id.days))

    @api.onchange('previous_activity_type_id')
    def _onchange_previous_activity_type_id(self):
        if self.previous_activity_type_id.next_type_ids:
            self.recommended_activity_type_id = self.previous_activity_type_id.next_type_ids[0]

    @api.onchange('recommended_activity_type_id')
    def _onchange_recommended_activity_type_id(self):
        self.activity_type_id = self.recommended_activity_type_id

    @api.multi
    def _check_access(self, operation):
        """ Rule to access activities

         * create: check write rights on related document;
         * write: rule OR write rights on document;
         * unlink: rule OR write rights on document;
        """
        self.check_access_rights(operation, raise_exception=True)  # will raise an AccessError

        if operation in ('write', 'unlink'):
            try:
                self.check_access_rule(operation)
            except exceptions.AccessError:
                pass
            else:
                return

        doc_operation = 'read' if operation == 'read' else 'write'
        activity_to_documents = dict()
        for activity in self.sudo():
            activity_to_documents.setdefault(activity.res_model, list()).append(activity.res_id)
        for model, res_ids in activity_to_documents.items():
            self.env[model].check_access_rights(doc_operation, raise_exception=True)
            try:
                self.env[model].browse(res_ids).check_access_rule(doc_operation)
            except exceptions.AccessError:
                raise exceptions.AccessError(
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') %
                    (self._description, operation))

    @api.model
    def create(self, values):
        # already compute default values to be sure those are computed using the current user
        values_w_defaults = self.default_get(self._fields.keys())
        values_w_defaults.update(values)

        # continue as sudo because activities are somewhat protected
        activity = super(MailActivity, self.sudo()).create(values_w_defaults)
        activity_user = activity.sudo(self.env.user)
        activity_user._check_access('create')
        self.env[activity_user.res_model].browse(activity_user.res_id).message_subscribe(partner_ids=[activity_user.user_id.partner_id.id])
        if activity.date_deadline <= fields.Date.today():
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                {'type': 'activity_updated', 'activity_created': True})
        return activity_user

    @api.multi
    def write(self, values):
        self._check_access('write')
        if values.get('user_id'):
            pre_responsibles = self.mapped('user_id.partner_id')
        res = super(MailActivity, self.sudo()).write(values)

        if values.get('user_id'):
            for activity in self:
                self.env[activity.res_model].browse(activity.res_id).message_subscribe(partner_ids=[activity.user_id.partner_id.id])
                if activity.date_deadline <= fields.Date.today():
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                        {'type': 'activity_updated', 'activity_created': True})
            for activity in self:
                if activity.date_deadline <= fields.Date.today():
                    for partner in pre_responsibles:
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner', partner.id),
                            {'type': 'activity_updated', 'activity_deleted': True})
        return res

    @api.multi
    def unlink(self):
        self._check_access('unlink')
        for activity in self:
            if activity.date_deadline <= fields.Date.today():
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', activity.user_id.partner_id.id),
                    {'type': 'activity_updated', 'activity_deleted': True})
        return super(MailActivity, self.sudo()).unlink()

    @api.multi
    def action_done(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback()

    def action_feedback(self, feedback=False):
        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env.ref('mail.mt_activities').id,
                mail_activity_type_id=activity.activity_type_id.id,
            )
            message |= record.message_ids[0]

        self.unlink()
        return message.ids and message.ids[0] or False

    @api.multi
    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def _action_notify(self):
        import lxml

        # classify activities to notify by type and main model
        activities_sudo = self.sudo()

        MailThread = self.env['mail.thread'].with_context(mail_notify_author=True)
        IrQweb = self.env['ir.qweb'].sudo()

        classified = dict()

        for activity in activities_sudo:
            act_type = activity.activity_type_id
            if not classified.get(act_type):
                classified[act_type] = dict()

            user = activity.user_id
            if not classified[act_type].get(user):
                classified[act_type][user] = dict()

            model = activity.res_model
            if not classified[act_type][user].get(model):
                classified[act_type][user][model] = list()

            classified[act_type][user][model].append(activity)

        for act_type, user_data in classified.items():
            template = act_type.reminder_html
            tree = lxml.html.fromstring(u'<t>%s</t>' % template)
            for user, model_data in user_data.items():
                variables = {'user': user}
                for activities in model_data:
                    variables['activity_count'] = len(activities)

                    rendered = IrQweb.render(tree, variables)

                    MailThread.message_notify(
                        body=rendered,
                        subject=_('Reminder for planned %s') % (act_type.display_name),
                        partner_ids=[activity.user_id.partner_id.id],
                    )

        self.write({'is_notified': True})


class MailActivityMixin(models.AbstractModel):
    """ Mail Activity Mixin is a mixin class to use if you want to add activities
    management on a model. It works like the mail.thread mixin. It defines
    an activity_ids one2many field toward activities using res_id and res_model_id.
    Various related / computed fields are also added to have a global status of
    activities on documents.

    Activities come with a new JS widget for the form view. It is integrated in the
    Chatter widget although it is a separate widget. It displays activities linked
    to the current record and allow to schedule, edit and mark done activities.
    Use widget="mail_activity" on activity_ids field in form view to use it.

    There is also a kanban widget defined. It defines a small widget to integrate
    in kanban vignettes. It allow to manage activities directly from the kanban
    view. Use widget="kanban_activity" on activitiy_ids field in kanban view to
    use it."""
    _name = 'mail.activity.mixin'
    _description = 'Activity Mixin'

    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user",
        domain=lambda self: [('res_model', '=', self._name)])
    activity_state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], string='State',
        compute='_compute_activity_state',
        groups="base.group_user",
        help='Status based on activities\nOverdue: Due date is already passed\n'
             'Today: Activity date is today\nPlanned: Future activities.')
    activity_user_id = fields.Many2one(
        'res.users', 'Responsible',
        related='activity_ids.user_id',
        search='_search_activity_user_id',
        groups="base.group_user")
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Next Activity Type',
        related='activity_ids.activity_type_id',
        search='_search_activity_type_id',
        groups="base.group_user")
    activity_date_deadline = fields.Date(
        'Next Activity Deadline', related='activity_ids.date_deadline',
        readonly=True, store=True,  # store to enable ordering + search
        groups="base.group_user")
    activity_summary = fields.Char(
        'Next Activity Summary',
        related='activity_ids.summary',
        search='_search_activity_summary',
        groups="base.group_user",)

    @api.depends('activity_ids.state')
    def _compute_activity_state(self):
        for record in self:
            states = record.activity_ids.mapped('state')
            if 'overdue' in states:
                record.activity_state = 'overdue'
            elif 'today' in states:
                record.activity_state = 'today'
            elif 'planned' in states:
                record.activity_state = 'planned'

    @api.model
    def _search_activity_user_id(self, operator, operand):
        return [('activity_ids.user_id', operator, operand)]

    @api.model
    def _search_activity_type_id(self, operator, operand):
        return [('activity_ids.activity_type_id', operator, operand)]

    @api.model
    def _search_activity_summary(self, operator, operand):
        return [('activity_ids.summary', operator, operand)]

    @api.multi
    def unlink(self):
        """ Override unlink to delete records activities through (res_model, res_id). """
        record_ids = self.ids
        result = super(MailActivityMixin, self).unlink()
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
        ).unlink()
        return result

    def action_schedule_activity(self, act_type_xmlid='', date_deadline=None, summary='', note='', **act_values):
        """ Schedule an activity on each record of the current record set.
        This method allow to provide as parameter act_type_xmlid. This is an
        xml_id of activity type instead of directly giving an activity_type_id.
        It is useful to avoid having various "env.ref" in the code and allow
        to let the mixin handle access rights.
        """
        if not date_deadline:
            date_deadline = fields.Date.today()
        if act_type_xmlid:
            activity_type = self.sudo().env.ref(act_type_xmlid)
        else:
            activity_type = self.env['mail.activity.type'].sudo().browse(act_values['activity_type_id'])

        model_id = self.env['ir.model']._get(self._name).id
        activities = self.env['mail.activity']
        for record in self:
            create_vals = {
                'activity_type_id': activity_type.id,
                'summary': summary or activity_type.summary,
                'note': note,
                'date_deadline': date_deadline,
                'res_model_id': model_id,
                'res_id': record.id,
            }
            create_vals.update(act_values)
            activities |= self.env['mail.activity'].create(create_vals)
        return activities

    def action_do_activity_ftypes(self, act_type_xmlids, user_id=None, feedback=None):
        """ Set activities as done, limiting to some activity types and
        optionally to a given user. """
        sudo_env = self.sudo()
        activity_types = self.env['mail.activity.type'].sudo()
        for act_type_xmlid in act_type_xmlids:
            activity_types |= sudo_env.env.ref(act_type_xmlid)
        domain = [
            '&', '&',
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('activity_type_id', 'in', activity_types.ids)
        ]
        if user_id:
            domain = ['&'] + domain + [('user_id', '=', user_id)]
        self.env['mail.activity'].search(domain).action_feedback(feedback=feedback)
        return True

    def action_cancel_activity_ftypes(self, act_type_xmlids, user_id=None):
        """ Unlink activities as done, limiting to some activity types and
        optionally to a given user. """
        sudo_env = self.sudo()
        activity_types = self.env['mail.activity.type'].sudo()
        for act_type_xmlid in act_type_xmlids:
            activity_types |= sudo_env.env.ref(act_type_xmlid)
        domain = [
            '&', '&',
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('activity_type_id', 'in', activity_types.ids)
        ]
        if user_id:
            domain = ['&'] + domain + [('user_id', '=', user_id)]
        self.env['mail.activity'].search(domain).unlink()
        return True

    def _cron_send_reminder_emails(self):
        activities = self.env['mail.activity'].sudo().search([
            ('date_deadline', '<=', date.today() + timedelta(days=1)),
            # ('is_notified', '=', False),
        ])
        activities._action_notify()
