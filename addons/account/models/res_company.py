# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    fiscal_localiazation = fields.Many2one('account.chart.template', string='Fiscal Localiazation')