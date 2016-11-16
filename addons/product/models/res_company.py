# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    def _default_weight_uom_id(self):
        kg_uom = self.env.ref('product.product_uom_kgm', raise_if_not_found=False)
        # necessary check as data not yet loaded on module installation
        if kg_uom:
            return kg_uom.id

    def _default_volume_uom_id(self):
        litre_uom = self.env.ref('product.product_uom_litre', raise_if_not_found=False)
        # necessary check as data not yet loaded on module installation
        if litre_uom:
            return litre_uom.id

    weight_uom_id = fields.Many2one(
        'product.uom', 'Weight unit of measure',
        default=_default_weight_uom_id,
        domain=lambda self: [('category_id', '=', self.env.ref('product.product_uom_categ_kgm').id)],
        help="This company will display weights in this unit of measure.")
    volume_uom_id = fields.Many2one(
        'product.uom', 'Volume unit of measure',
        default=_default_volume_uom_id,
        domain=lambda self: [('category_id', '=', self.env.ref('product.product_uom_categ_vol').id)],
        help="This company will display volumes in this unit of measure.")

    @api.model
    def create(self, vals):
        new_company = super(ResCompany, self).create(vals)
        ProductPricelist = self.env['product.pricelist']
        pricelist = ProductPricelist.search([('currency_id', '=', new_company.currency_id.id), ('company_id', '=', False)], limit=1)
        if not pricelist:
            pricelist = ProductPricelist.create({
                'name': new_company.name,
                'currency_id': new_company.currency_id.id,
            })
        field = self.env['ir.model.fields']._get('res.partner', 'property_product_pricelist')
        self.env['ir.property'].create({
            'name': 'property_product_pricelist',
            'company_id': new_company.id,
            'value_reference': 'product.pricelist,%s' % pricelist.id,
            'fields_id': field.id
        })
        return new_company

    @api.multi
    def write(self, values):
        # When we modify the currency of the company, we reflect the change on the list0 pricelist, if
        # that pricelist is not used by another company. Otherwise, we create a new pricelist for the
        # given currency.
        ProductPricelist = self.env['product.pricelist']
        currency_id = values.get('currency_id')
        main_pricelist = self.env.ref('product.list0', False)
        if currency_id and main_pricelist:
            nb_companies = self.search_count([])
            for company in self:
                existing_pricelist = ProductPricelist.search(
                    [('company_id', 'in', (False, company.id)),
                     ('currency_id', '=', currency_id)])
                if existing_pricelist:
                    continue
                if currency_id == company.currency_id.id:
                    continue
                currency_match = main_pricelist.currency_id == company.currency_id
                company_match = (main_pricelist.company_id == company or
                                 (main_pricelist.company_id.id is False and nb_companies == 1))
                if currency_match and company_match:
                    main_pricelist.write({'currency_id': currency_id})
                else:
                    params = {
                        'currency': self.env['res.currency'].browse(currency_id).name,
                        'company': company.name
                    }
                    pricelist = ProductPricelist.create({
                        'name': _("Default %(currency)s pricelist for %(company)s") % params,
                        'currency_id': currency_id,
                        'company_id': company.id,
                    })
                    field = self.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_product_pricelist')])
                    self.env['ir.property'].create({
                        'name': 'property_product_pricelist',
                        'company_id': company.id,
                        'value_reference': 'product.pricelist,%s' % pricelist.id,
                        'fields_id': field.id
                    })
        return super(ResCompany, self).write(values)
