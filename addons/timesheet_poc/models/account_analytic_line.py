# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    work_logger_id = fields.Many2one('work.logger')
    work_manager_id = fields.Many2one('work.manager')

    @api.onchange('work_manager_id')
    def onchange_work_manager_id(self):
        self.resource_logger_id = False
        self.account_id = self.work_manager_id.analytic_account_id.id

    @api.model
    def create(self, vals):
        if vals.get('work_manager_id'):
            work_manager = self.env['work.manager'].browse(vals.get('work_manager_id'))
            vals['account_id'] = work_manager.analytic_account_id.id
        return super(AccountAnalyticLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('work_manager_id'):
            work_manager = self.env['work.manager'].browse(vals.get('work_manager_id'))
            vals['account_id'] = work_manager.analytic_account_id.id
        return super(AccountAnalyticLine, self).write(vals)
