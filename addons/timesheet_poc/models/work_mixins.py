# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WorkLogger(models.Model):
    _inherit = 'work.logger'

    timesheet_ids = fields.One2many(
        'account.analytic.line', 'work_logger_id', 'Timesheets')


class WorkLoggerMixin(models.AbstractModel):
    _inherit = 'work.logger.mixin'

    work_timesheet_ids = fields.One2many(related='work_logger_id.timesheet_ids')


class WorkManager(models.Model):
    _inherit = 'work.manager'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Contract/Analytic',
        help="Link to an analytic account if financial management on projects is required."
             "It enables you to make budgets, planning, cost and revenue analysis, timesheeting, etc.",
        ondelete="cascade", required=True,
        auto_join=True)
    timesheet_ids = fields.One2many(
        'account.analytic.line', 'work_manager_id', 'Timesheets')


class WorkManagerMixin(models.AbstractModel):
    _inherit = 'work.manager.mixin'

    work_timesheet_ids = fields.One2many(related='work_manager_id.timesheet_ids')

    @api.model_cr_context
    def _init_column(self, name):
        """ Create aliases for existing rows. """
        super(WorkManagerMixin, self)._init_column(name)
        if name != 'work_manager_id':
            return

        ChildModel = self.sudo().with_context({
            'active_test': False,       # retrieve all records
            'prefetch_fields': False,   # do not prefetch fields on records
        })

        for record in ChildModel.search([('work_manager_id', '!=', False), ('work_manager_id.analytic_account_id', '=', False)]):
            record.work_manager_id.update(record.work_get_manager_values())
            _logger.info('Work Manager analytic account updated for %s %s (id %s)',
                         record._name, record.display_name, record.id)

    def action_see_timesheets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Timesheets',
            'res_model': 'account.analytic.line',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'view_ids': [
                (5, 0),
                (0, 0, {'view_mode': 'tree', 'view_id': self.env.ref('timesheet_poc.account_analytic_line_view_tree_generic').id})
            ],
            'domain': [('work_manager_id', '=', self.work_manager_id.id)],
            'context': {
                'default_work_manager_id': self.work_manager_id.id,
            }
        }
