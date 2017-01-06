# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Project(models.Model):
    _name = 'project.project'
    _inherit = ['work.manager.mixin', 'project.project']

    def work_get_manager_values(self):
        res = super(Project, self).work_get_manager_values()
        res.update({
            'manager_type': 'project_project',
            'analytic_account_id': self.id,
        })
        return res


class Task(models.Model):
    _name = 'project.task'
    _inherit = ['work.logger.mixin', 'project.task']
