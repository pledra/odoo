# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

UBL_COUNTRIES = [
    'BE',
]

UBL_INVOICE_ATTACHMENT = (
    'UBL-Invoice-2.1.xml',
    'edi_ubl/data/templates/2.1/UBL-Invoice-2.1.xml',
    'edi_ubl/data/xsd/2.1/maindoc/UBL-Invoice-2.1.xsd'
)

class BaseEdi(models.Model):
    _inherit = 'base.edi'

    @api.model
    def edi_generate_invoice_attachments(self):
        ''' Generates invoice attachment for countries that use UBL.
        '''
        super(BaseEdi, self).edi_generate_invoice_attachments()
        country_code = self.partner_id.country_id.code
        if country_code in UBL_COUNTRIES:
            self.edi_create_attachment(
                UBL_INVOICE_ATTACHMENT[0],
                UBL_INVOICE_ATTACHMENT[1],
                UBL_INVOICE_ATTACHMENT[2]
                )

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
        ''' Override '''
        template_data = super(BaseEdi, self).edi_create_template_data()
        template_data['version_id'] = 2.1
        template_data['currency_name'] = self.currency_id.name
        self._ubl_append_party_data(
            self.company_id.partner_id, 'supplier', template_data)
        self._ubl_append_party_data(
            self.partner_id, 'customer', template_data)
        return template_data