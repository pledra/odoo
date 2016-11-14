# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from lxml import etree
import copy

UBL_INVOICE_DOC_REF_ID = 'edi_ubl.ubl_document_reference'

UBL_INVOICE_ATTACHMENT = (
    'UBL-Invoice-2.1.xml',
    'edi_ubl.ubl_invoice',
    'edi_ubl/data/xsd/2.1/maindoc/UBL-Invoice-2.1.xsd'
)

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    @api.model
    def _ubl_get_type_code(self):
        ''' Get the type of the invoice.
        '''
        return 380 if self.type == 'out_invoice' else 381

    @api.model
    def _edi_generate_attachment_with_embedding(self):
        ''' This method is used to implement a particular case of the UBL.
        Indeed, a copy of the xml must be embedded in the xml itself as a pdf
        document. To do that, the tree:
        - Created like the normal case
        - A copy of this tree is created and the 'AdditionalDocumentReference' element
        is removed.
        - The tree is embedded in the original tree as a pdf document by overriding the
        content of the 'EmbeddedDocumentBinaryObject' element.
        '''
        # Build main tree
        tree = self.edi_load_rendered_template(
            xml_id=UBL_INVOICE_ATTACHMENT[1],
            as_tree=True)

        # Create binary attachment content
        tree_to_embed = copy.deepcopy(tree)
        doc_ref_node = tree_to_embed.find(
            self.UBL_NAMESPACES['cac'] + 'AdditionalDocumentReference')
        tree_to_embed.remove(doc_ref_node)
        content_to_embed = self.edi_create_embedded_pdf_in_xml_content(
            'account.report_invoice', 
            UBL_INVOICE_ATTACHMENT[0], 
            self.edi_as_str(tree_to_embed))

        # # Add the binary content to the main tree
        doc_ref_node = tree.find(
            './/' + self.UBL_NAMESPACES['cbc'] + 'EmbeddedDocumentBinaryObject')
        doc_ref_node.text = content_to_embed

        # Create attachment
        self.edi_create_attachment(
            UBL_INVOICE_ATTACHMENT[0],
            content_tree=tree,
            xsd_path=UBL_INVOICE_ATTACHMENT[2])

    @api.model
    def edi_generate_attachments(self):
        '''Override'''
        super(AccountInvoice, self).edi_generate_attachments()
        country_code = self.partner_id.country_id.code
        if country_code in self.UBL_COUNTRIES:
            self._edi_generate_attachment_with_embedding()

    @api.model
    def edi_create_values(self):
        '''Override'''
        values = super(AccountInvoice, self).edi_create_values()
        values['type_code'] = self._ubl_get_type_code()

        precision_digits = self.env['decimal.precision'].precision_get('Account')

        # Append values related to taxes
        values['amount_tax'] = self.amount_tax
        values['amount_untaxed'] = \
            '%0.*f' % (precision_digits, self.amount_untaxed)
        values['amount_total'] = \
            '%0.*f' % (precision_digits, self.amount_total)
        values['residual'] = \
            '%0.*f' % (precision_digits, self.residual)
        values['amount_prepaid'] = \
            '%0.*f' % (precision_digits, self.amount_total - self.residual)

        # Append values related to document reference
        values['doc_ref_id'] = 'Invoice-' + self.number + '.pdf'
        values['attach_binary'] = 'TO FILL MANUALLY'

        # Append values related to invoice lines
        values['invoice_lines_values'] = []
        line_number = 0
        for invoice_line_id in self.invoice_line_ids:
            line_number += 1
            values_line = invoice_line_id.edi_create_values()
            values_line['line_number'] = line_number
            subvalues = self.edi_as_subvalues(values_line)
            values['invoice_lines_values'].append(subvalues)

        return values

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _ubl_get_description(self):
        ''' Return an one-line description
        '''
        lines = map(lambda line: line.strip(), self.name.split('\n'))
        return ', '.join(lines)

    @api.model
    def _ubl_get_product_name(self):
        ''' Return a product name more advanced if the product has variants
        '''
        variants = [variant.name for variant in self.product_id.attribute_value_ids]
        if variants:
            return "%s (%s)" % (self.product_id.name, ', '.join(variants))
        else:
            return self.product_id.name

    @api.model
    def edi_create_values(self):
        ''' This method returns the values about the invoice_line.
        '''
        values = {}
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        partner_id = self.invoice_id.partner_id
        res_taxes = self.invoice_line_tax_ids.compute_all(
            self.price_subtotal, 
            quantity=self.quantity, 
            product=self.product_id, 
            partner=partner_id)
        values['quantity'] = self.quantity
        values['price_subtotal'] = \
            '%0.*f' % (precision_digits, self.price_subtotal)
        values['total_excluded'] =  tools.float_round(
            res_taxes['total_excluded'], 
            precision_digits=precision_digits) 
        values['amount_tax'] = tools.float_round(
            res_taxes['total_excluded'] - res_taxes['total_included'], 
            precision_digits=precision_digits)
        values['description'] = self._ubl_get_description()
        values['name'] = self._ubl_get_product_name()
        values['identification_id'] = self.product_id.default_code
        values['product_id'] = self.product_id
        return values