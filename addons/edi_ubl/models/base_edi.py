# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools


class BaseEdi(models.Model):
    _inherit = 'base.edi'

    UBL_COUNTRIES = [
        'BE',
    ]

    UBL_NAMESPACES = {
        'cac': '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}',
        'cbc': '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}',
    }

    UBL_BLOCKS = {
        'REF': 'edi_ubl/data/templates/2.1/UBL-Additional-Reference-Block.xml',
        'PARTY': 'edi_ubl/data/templates/2.1/UBL-Party-Block.xml',
    }        

    @api.model
    def _ubl_append_party_block(self, partner_id, tree_node, insert_index=None):
        template_data = {'party': partner_id}
        self.edi_append_block(
            tree_node, self.UBL_BLOCKS['PARTY'], template_data, insert_index=insert_index)

    @api.model
    def edi_create_template_data(self):
        template_data = super(BaseEdi, self).edi_create_template_data()
        template_data['version_id'] = 2.1
        template_data['currency_name'] = self.currency_id.name
        return template_data