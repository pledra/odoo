# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

UBL_COUNTRIES = [
    'BE',
]

UBL_INVOICE_ATTACHMENT = (
    'UBL-Invoice-2.1.xml',
    'base_ubl/data/templates/2.1/UBL-Invoice-2.1.xml',
    'base_ubl/data/xsd/2.1/maindoc/UBL-Invoice-2.1.xsd'
)

class BaseEdi(models.Model):
    _inherit = 'base.edi'

    def edi_invoice_validate(self):
        super(BaseEdi, self).edi_invoice_validate()
        country_code = self.partner_id.country_id.code
        if country_code in UBL_COUNTRIES:
            pass
        # TEST
        self.create_attachment(
            UBL_INVOICE_ATTACHMENT[0],
            UBL_INVOICE_ATTACHMENT[1],
            UBL_INVOICE_ATTACHMENT[2]
            )
        return

    def create_template_data(self):
        template_data = super(BaseEdi, self).create_template_data()
        template_data['ubl_supplier'] = \
            self.company_id.partner_id
        template_data['ubl_com_supplier'] = \
            self.company_id.partner_id.commercial_partner_id
        template_data['ubl_supplier_phone'] = \
            template_data['ubl_supplier'].phone or \
            template_data['ubl_com_supplier'].phone
        template_data['ubl_supplier_fax'] = \
            template_data['ubl_supplier'].fax or \
            template_data['ubl_com_supplier'].fax
        template_data['ubl_supplier_email'] = \
            template_data['ubl_supplier'].email or \
            template_data['ubl_com_supplier'].email
        template_data['ubl_customer'] = \
            self.partner_id
        template_data['ubl_com_customer'] = \
            self.partner_id.commercial_partner_id
        template_data['ubl_customer_phone'] = \
            template_data['ubl_customer'].phone or \
            template_data['ubl_com_customer'].phone
        template_data['ubl_customer_fax'] = \
            template_data['ubl_customer'].fax or \
            template_data['ubl_com_customer'].fax
        template_data['ubl_customer_email'] = \
            template_data['ubl_customer'].email or \
            template_data['ubl_com_customer'].email
        return template_data