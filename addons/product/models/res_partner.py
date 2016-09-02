# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    # property_product_pricelist = fields.Many2one(
    #     'product.pricelist', 'Sale Pricelist', compute='_compute_product_pricelist',
    #     inverse="_inverse_product_pricelist", company_dependent=False,  # needed to disable the property
    #     help="This pricelist will be used, instead of the default one, for sales to the current partner")

    property_product_pricelist = fields.Many2one(
        'product.pricelist', 'Sale Pricelist', company_dependent=True,
        help="This pricelist will be used, instead of the default one, for sales to the current partner")

    @api.multi
    def _compute_product_pricelist(self):
        for p in self:
            p.property_product_pricelist = self.env['product.pricelist'].get_partner_pricelist(p.id)

    @api.one
    def _inverse_product_pricelist(self):
        self.env['ir.property'].set_multi('property_product_pricelist', self._name, {self.id: self.property_product_pricelist})

    def _commercial_fields(self):
        return super(Partner, self)._commercial_fields() + ['property_product_pricelist']
