# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    @api.model
    def _edi_get_type_code(self):
        return 380 if self.type == 'out_invoice' else 381

    @api.model
    def _edi_append_headers(self, template_data):
        template_data['id'] = self.number
        template_data['issuedate'] = self.date_invoice
        template_data['type_code'] = self._edi_get_type_code()
        template_data['comment'] = self.comment

    @api.model
    def _edi_append_tax_data(self, template_data):
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
    def _edi_append_invoice_lines(self, template_data):
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
        self._edi_append_headers(template_data)
        self._edi_append_tax_data(template_data)
        self._edi_append_invoice_lines(template_data)
        return template_data

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _edi_get_description(self):
        lines = map(lambda line: line.strip(), self.name.split('\n'))
        return ', '.join(lines)

    @api.model
    def _edi_get_product_name(self):
        variants = [variant.name for variant in self.product_id.attribute_value_ids]
        if variants:
            return "%s (%s)" % (self.product_id.name, ', '.join(variants))
        else:
            return self.product_id.name

    @api.model
    def _edi_append_invoice_line_data(self, template_data):
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