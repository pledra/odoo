# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TimesheetPack(models.Model):
    _name = 'timesheet.pack'

    name = fields.Char()
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Contract/Analytic',
        auto_join=True,
        ondelete="restrict", required=True,
        help="UPDATE ME",
    )
    timesheet_line_ids = fields.One2many(
        'account.analytic.line', 'timesheet_pack_id',
        'Timesheet Lines',
        help="UPDATE ME"
    )
