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

    unece_code_payment_means_ids = fields.Many2many('unece.code',
        string='UNECE Tax Type',
        domain=[('type_id.name', '=', 'UN/ECE 4461')],
        help="Select the Payment Means Code of the official "
        "nomenclature of the United Nations Economic "
        "Commission for Europe (UNECE), DataElement 4461")

    @api.model
    def _ubl_get_type_code(self):
        ''' Get the type of the invoice.
        '''
        return 380 if self.type == 'out_invoice' else 381

    @api.model
    def _ubl_get_notes(self):
        return [self.comment] if self.comment else []

    @api.model
    def _ubl_get_add_document_ref(self):
        return self.edi_as_subvalues({
            'doc_ref_id': 'Invoice-' + self.number + '.pdf',
            'attach_binary': ''
        })

    @api.model
    def _ubl_get_payment_means(self):
        return [
            self.edi_as_subvalues({'date_due': self.date_due, 'unece_code': i}) 
            for i in self.unece_code_payment_means_ids]

    @api.model
    def _ubl_get_tax_total(self):
        return self.edi_as_subvalues({'amount_tax': self.amount_tax})

    @api.model
    def _ubl_get_monetary(self):
        precision_digits = self.env['decimal.precision'].precision_get('Account')
        return self.edi_as_subvalues({
            'amount_untaxed': '%0.*f' % (precision_digits, self.amount_untaxed),
            'amount_total': '%0.*f' % (precision_digits, self.amount_total),
            'residual': '%0.*f' % (precision_digits, self.residual),
            'amount_prepaid': '%0.*f' % (precision_digits, self.amount_total - self.residual),
        })

    @api.model
    def _ubl_get_iline_notes(self, invoice_line_id):
        # TODO: if discount, promotions, lots...etc ... add infos here
        # The result must be an array
        notes = []

        # Check for discount
        if invoice_line_id.discount:
            notes.append('Discount (%s %)' % invoice_line_id.discount)

        return notes

    @api.model
    def _ubl_get_iline_description(self, invoice_line_id):
        ''' Return an one-line description
        '''
        lines = map(lambda line: line.strip(), invoice_line_id.name.split('\n'))
        return ', '.join(lines)

    @api.model
    def _ubl_get_iline_product_name(self, invoice_line_id):
        ''' Return a product name more advanced if the product has variants
        '''
        product_id = invoice_line_id.product_id
        variants = [variant.name for variant in product_id.attribute_value_ids]
        if variants:
            return "%s (%s)" % (product_id.name, ', '.join(variants))
        else:
            return product_id.name

    @api.model
    def _ubl_get_iline_item(self, invoice_line_id):
        return self.edi_as_subvalues({
            'description': self._ubl_get_iline_description(invoice_line_id),
            'name': self._ubl_get_iline_product_name(invoice_line_id),
            'identification_id': invoice_line_id.product_id.default_code,
            'product_id': invoice_line_id.product_id,
        })

    @api.model
    def _ubl_get_iline_amount_tax(self, tax_ids, invoice_line_id):
        res_taxes = tax_ids.compute_all(
            invoice_line_id.price_unit, 
            quantity=invoice_line_id.quantity, 
            product=invoice_line_id.product_id, 
            partner=invoice_line_id.invoice_id.partner_id)

        amount_tax = res_taxes['total_included'] - invoice_line_id.price_subtotal

        values_array = []
        for tax in res_taxes['taxes']:
            tax_id = self.env['account.tax'].browse(tax['id'])
            values = {
                'amount_tax': amount_tax,
                'taxable_amount': res_taxes['base'],
                'unece_code': tax_id.unece_code_category_id,
                'tax_name': tax_id.name,
                }
            if tax_id.amount_type == 'percent':
                values['tax_percent'] = tax_id.amount
                values['taxes'] = []
            elif tax_id.amount_type == 'group':
                tax_id.children_tax_ids.with_context(
                    base_values=(
                        res_taxes['total_excluded'], 
                        res_taxes['total_included'], 
                        res_taxes['base']))
                values['taxes'] = \
                    self._ubl_get_amount_tax(
                        tax_id.children_tax_ids, invoice_line_id)
            values_array.append(self.edi_as_subvalues(values))
        return values_array

    @api.model
    def _ubl_get_invoice_lines(self):
        values = []
        identifier = 0
        for invoice_line_id in self.invoice_line_ids:
            identifier += 1
            values.append(self.edi_as_subvalues({
                'id': identifier,
                'uuid': self._ubl_get_uuid(),
                'notes': self._ubl_get_iline_notes(invoice_line_id),
                'quantity': invoice_line_id.quantity,
                'subtotal': invoice_line_id.price_subtotal,
                'taxes': self._ubl_get_iline_amount_tax(
                    invoice_line_id.invoice_line_tax_ids, invoice_line_id),
                'item': self._ubl_get_iline_item(invoice_line_id),
            }))
        return values

    @api.model
    def _ubl_generate_attachment_with_embedding(self):
        ''' This method is used to implement a particular case of the UBL.
        Indeed, a copy of the xml must be embedded in the xml itself as a pdf
        document. To do that, the tree:
        - Created like the normal case
        - A copy of this tree is created and the 'AdditionalDocumentReference' element
        is removed.
        - The tree is embedded in the original tree as a pdf document by overriding the
        content of the 'EmbeddedDocumentBinaryObject' element.
        '''
        values = self.ubl_create_values()

        # Build main tree
        tree = self.edi_load_rendered_template(
            values = values,
            xml_id=UBL_INVOICE_ATTACHMENT[1],
            as_tree=True,
            ns_refactoring=self.UBL_NS_REFACTORING)

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
            self._ubl_generate_attachment_with_embedding()

    @api.model
    def ubl_create_values(self):
        '''Override'''
        values = super(AccountInvoice, self).ubl_create_values()
        values['id'] = self.number
        values['issue_date'] = self.date_invoice
        values['type_code'] = self._ubl_get_type_code()
        values['notes'] = self._ubl_get_notes()
        values['doc_ref'] = self._ubl_get_add_document_ref()
        values['payment_means'] = self._ubl_get_payment_means()
        values['tax_total'] = self._ubl_get_tax_total()
        values['monetary'] = self._ubl_get_monetary()
        values['invoice_lines'] = self._ubl_get_invoice_lines()
        values['vat_unece'] = self.env.ref('edi_ubl.code_type_tax_vat')
        return values