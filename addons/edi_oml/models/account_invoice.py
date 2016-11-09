# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

OML_ADDENDA = {
    'AUTOZONE': (
        'OML-Invoice-Autozone.xml',
        'edi_oml/data/templates/OML-Invoice-Autozone.xml',
        None
        # 'edi_oml/data/xsd/OML-Invoice.xsd'
    )
}

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    @api.model
    def edi_generate_attachments(self):
        ''' Generates invoice attachment for countries that use UBL.
        '''
        super(AccountInvoice, self).edi_generate_attachments()
        country_code = self.partner_id.country_id.code
        if country_code == 'MX':
            pass
        # TEST
        for key, value in OML_ADDENDA.items():
            self.edi_create_attachment(
                value[0], 
                value[1], 
                xsd_path=value[2]
                )

    @api.model
    def edi_create_template_data(self):
        ''' Override '''
        template_data = super(AccountInvoice, self).edi_create_template_data()
        template_data['domicile'] = 'TODO'
        template_data['currency_name'] = self.currency_id.name
        template_data['account'] = 'TODO'
        template_data['rate'] = 'TODO'
        template_data['certificate'] = 'TODO'
        template_data['certificate_number'] = 'TODO'
        template_data['discount_amount'] = 'TODO'
        template_data['discount_amount_subtotal'] = 'TODO'
        template_data['issuedate'] = self.date_invoice
        template_data['id'] = self.number
        template_data['payment_policy'] = 'TODO'
        template_data['payment_method'] = 'TODO'
        template_data['serie'] = 'TODO'
        template_data['document_type'] = 'TODO'
        template_data['amount_total'] = 'TODO'
        template_data['supplier'] = \
            self.company_id.partner_id.commercial_partner_id
        template_data['customer'] = \
            self.partner_id.commercial_partner_id
        return template_data