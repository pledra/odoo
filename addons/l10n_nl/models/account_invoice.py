# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    cbs_export_id = fields.Many2one('l10n_nl.cbs.export', 'CBS Export')
