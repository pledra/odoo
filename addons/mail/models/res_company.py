# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class Company(models.Model):
    _inherit = 'res.company'

    mail_template_layout = fields.Html()
