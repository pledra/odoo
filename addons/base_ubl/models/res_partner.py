# -*- coding: utf-8 -*-

from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    unece_code_tax_ids = fields.Many2many('unece.code',
        string='UNECE Tax Type',
        domain=[('type_id.name', '=', 'UN/ECE 5153')],
        help="Select the Tax Type Code of the official "
        "nomenclature of the United Nations Economic "
        "Commission for Europe (UNECE), DataElement 5153")