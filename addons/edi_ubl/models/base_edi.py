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

    @api.model
    def edi_refactoring_ns_map(self):
        '''Override'''
        ns_refactoring = super(BaseEdi, self).edi_refactoring_ns_map()
        ns_refactoring['cbc__'] = 'cbc'
        ns_refactoring['cac__'] = 'cac'
        return ns_refactoring

    @api.model
    def edi_create_values(self):
        '''Override'''
        values = super(BaseEdi, self).edi_create_values()
        values['version_id'] = 2.1
        values['currency_name'] = self.currency_id.name
        values['supplier_party'] = \
            self.company_id.partner_id.commercial_partner_id
        values['customer_party'] = \
            self.partner_id.commercial_partner_id
        return values