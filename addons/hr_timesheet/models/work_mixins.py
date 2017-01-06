# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WorkManager(models.Model):
    _name = 'work.manager'
    _inherit = 'work.manager'

    manager_type = fields.Selection(
        selection_add=[('project_project', 'Project')])
