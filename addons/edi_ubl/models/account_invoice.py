# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

UBL_INVOICE_ATTACHMENT = (
    'UBL-Invoice-2.1.xml',
    'edi_ubl/data/templates/2.1/UBL-Invoice-2.1.xml',
    'edi_ubl/data/xsd/2.1/maindoc/UBL-Invoice-2.1.xsd'
)

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    @api.model
    def _ubl_append_reference_block(self, tree_node, content, insert_index):
        ''' This method appends manually the additional document reference to
        the etree.
        '''
        # Creation of the data
        template_data = {
            'doc_reference': 'Invoice-' + self.number + '.pdf',
            'binary_content': self.edi_create_embedded_pdf_in_xml_content(
                'account.report_invoice', UBL_INVOICE_ATTACHMENT[0], content)
        }
        # Append block
        self.edi_append_block(
            tree_node, self.UBL_BLOCKS['REF'], template_data, insert_index=insert_index)

    @api.model
    def _ubl_create_attachment_with_embedding(
        self, xml_filename, template_path, xsd_path=None):
        ''' UBL needs that a copy of the xml is embedded as a pdf in the xml itself.
        So, we must add a custom section in the xml tree containing this embedding.
        '''
        # Creation of the data
        template_data = self.edi_create_template_data()
        # Creation of the etree
        ubl_tree = self.edi_load_template_tree(
            UBL_INVOICE_ATTACHMENT[1], template_data, UBL_INVOICE_ATTACHMENT[2])

        # ADD supplier party block
        supplier_party_node = ubl_tree.find(
            self.UBL_NAMESPACES['cac'] + 'AccountingSupplierParty')
        com_supplier = self.company_id.partner_id.commercial_partner_id

        self._ubl_append_party_block(com_supplier, supplier_party_node)

        # ADD customer party block
        customer_party_node = ubl_tree.find(
            self.UBL_NAMESPACES['cac'] + 'AccountingCustomerParty')
        com_customer = self.partner_id.commercial_partner_id
        self._ubl_append_party_block(com_customer, customer_party_node)

        # ADD reference block
        content = self.edi_create_str_from_tree(ubl_tree)
        doc_currency_node = ubl_tree.find(
            self.UBL_NAMESPACES['cbc'] + 'DocumentCurrencyCode')
        doc_currency_index = ubl_tree.index(doc_currency_node)
        self._ubl_append_reference_block(
            ubl_tree, content, doc_currency_index + 1)

        # Update the content
        content = self.edi_create_str_from_tree(ubl_tree)

        # Create the attachment
        self.edi_create_attachment(
            xml_filename, content=content)

    @api.model
    def edi_generate_attachments(self):
        ''' Generates invoice attachment for countries that use UBL.
        '''
        super(AccountInvoice, self).edi_generate_attachments()
        country_code = self.partner_id.country_id.code
        if country_code in self.UBL_COUNTRIES:
            self._ubl_create_attachment_with_embedding(
                UBL_INVOICE_ATTACHMENT[0],
                UBL_INVOICE_ATTACHMENT[1],
                UBL_INVOICE_ATTACHMENT[2]
                )

    @api.model
    def _edi_get_type_code(self):
        return 380 if self.type == 'out_invoice' else 381

    @api.model
    def _edi_append_headers_data(self, template_data):
        template_data['id'] = self.number
        template_data['issuedate'] = self.date_invoice
        template_data['type_code'] = self._edi_get_type_code()
        template_data['comment'] = self.comment

    @api.model
    def _edi_append_tax_data(self, template_data):
        ''' Append data about the taxes
        '''
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        template_data['amount_tax'] = self.amount_tax
        template_data['amount_untaxed'] = \
            '%0.*f' % (precision_digits, self.amount_untaxed)
        template_data['amount_total'] = \
            '%0.*f' % (precision_digits, self.amount_total)
        template_data['residual'] = \
            '%0.*f' % (precision_digits, self.residual)
        template_data['amount_prepaid'] = \
            '%0.*f' % (precision_digits, self.amount_total - self.residual)

    @api.model
    def _edi_append_invoice_lines_data(self, template_data):
        ''' Append data about the invoice_line_ids
        '''
        template_data['invoice_lines'] = []
        line_number = 0
        for invoice_line_id in self.invoice_line_ids:
            line_number += 1
            template_data_line = {'number': line_number}
            invoice_line_id._edi_append_invoice_line_data(template_data_line)
            template_data['invoice_lines'].append(template_data_line)

    @api.model
    def edi_create_template_data(self):
        ''' Override '''
        template_data = super(AccountInvoice, self).edi_create_template_data()
        self._edi_append_headers_data(template_data)
        self._edi_append_tax_data(template_data)
        self._edi_append_invoice_lines_data(template_data)
        return template_data

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _edi_get_description(self):
        ''' Return an one-line description
        '''
        lines = map(lambda line: line.strip(), self.name.split('\n'))
        return ', '.join(lines)

    @api.model
    def _edi_get_product_name(self):
        ''' Return a product name more advanced if the product has variants
        '''
        variants = [variant.name for variant in self.product_id.attribute_value_ids]
        if variants:
            return "%s (%s)" % (self.product_id.name, ', '.join(variants))
        else:
            return self.product_id.name

    @api.model
    def _edi_append_invoice_line_data(self, template_data):
        ''' This method adds informations about the invoice_line to fill the template.
        '''
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        partner_id = self.invoice_id.partner_id
        res_taxes = self.invoice_line_tax_ids.compute_all(
            self.price_subtotal, 
            quantity=self.quantity, 
            product=self.product_id, 
            partner=partner_id)
        template_data['quantity'] = self.quantity
        template_data['price_subtotal'] = \
            '%0.*f' % (precision_digits, self.price_subtotal)
        template_data['total_excluded'] =  tools.float_round(
            res_taxes['total_excluded'], 
            precision_digits=precision_digits) 
        template_data['total_tax'] = tools.float_round(
            res_taxes['total_excluded'] - res_taxes['total_included'], 
            precision_digits=precision_digits)
        template_data['description'] = self._edi_get_description()
        template_data['product_name'] = self._edi_get_product_name()
        template_data['seller_code'] = self.product_id.default_code
        template_data['product'] = self.product_id