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
    def _ubl_append_party_data(self, partner_id, tag, template_data):
        template_data[tag + '_com'] = \
            partner_id.commercial_partner_id
        template_data[tag + '_phone'] = \
            partner_id.phone or \
            template_data[tag + '_com'].phone
        template_data[tag + '_fax'] = \
            partner_id.fax or \
            template_data[tag + '_com'].fax
        template_data[tag + '_email'] = \
            partner_id.email or \
            template_data[tag + '_com'].email

    @api.model
    def edi_create_template_data(self):
        template_data = super(BaseEdi, self).edi_create_template_data()
        template_data['version_id'] = 2.1
        template_data['currency_name'] = self.currency_id.name
        self._ubl_append_party_data(
            self.company_id.partner_id, 'supplier', template_data)
        self._ubl_append_party_data(
            self.partner_id, 'customer', template_data)
        return template_data