# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    company_share_product = fields.Boolean(
        'Share product to all companies',
        help="Share your product to all companies defined in your instance.\n"
             " * Checked : Product are visible for every company, even if a company is defined on the partner.\n"
             " * Unchecked : Each company can see only its product (product where company is defined). Product not related to a company are visible for all companies.")
    database_weight_uom_id = fields.Many2one(
        'product.uom', 'Database weight unit of measure',
        domain=lambda self: [('category_id', '=', self.env.ref('product.product_uom_categ_kgm').id)],
        help="Odoo will store weights in this unit of measure and set it as reference.")
    database_volume_uom_id = fields.Many2one(
        'product.uom', 'Database volume unit of measure',
        domain=lambda self: [('category_id', '=', self.env.ref('product.product_uom_categ_vol').id)],
        help="Odoo will store volumes in this unit of measure and set it as reference.")
    weight_uom_id = fields.Many2one(related='company_id.weight_uom_id')
    volume_uom_id = fields.Many2one(related='company_id.volume_uom_id')

    @api.model
    def get_default_database_weight_uom_id(self, fields):
        return {
            'database_weight_uom_id': int(self.env['ir.config_parameter'].get_param('database_weight_uom_id', default=self.env.ref('product.product_uom_kgm').id))
        }

    @api.multi
    def set_database_weight_uom_id(self):
        self.env['ir.config_parameter'].set_param('database_weight_uom_id', self.database_weight_uom_id.id)
        update_factor = 1.0 / self.database_weight_uom_id.factor
        weight_uoms = self.env['product.uom'].search([('category_id', '=', self.env.ref('product.product_uom_categ_kgm').id)])
        for uom in weight_uoms:
            uom.factor *= update_factor
            if uom.factor < 1:
                uom.uom_type = 'bigger'
            elif uom.factor > 1:
                uom.uom_type = 'smaller'
        self.database_weight_uom_id.uom_type = 'reference'

    @api.model
    def get_default_database_volume_uom_id(self, fields):
        return {
            'database_volume_uom_id': int(self.env['ir.config_parameter'].get_param('database_volume_uom_id', default=self.env.ref('product.product_uom_litre').id))
        }

    @api.multi
    def set_database_volume_uom_id(self):
        self.env['ir.config_parameter'].set_param('database_volume_uom_id', self.database_volume_uom_id.id)
        update_factor = 1.0 / self.database_volume_uom_id.factor
        volume_uoms = self.env['product.uom'].search([('category_id', '=', self.env.ref('product.product_uom_categ_vol').id)])
        for uom in volume_uoms:
            uom.factor *= update_factor
            if uom.factor < 1:
                uom.uom_type = 'bigger'
            else:
                uom.uom_type = 'smaller'
        self.database_weight_uom_id.uom_type = 'reference'

    @api.model
    def get_default_company_share_product(self, fields):
        product_rule = self.env.ref('product.product_comp_rule')
        return {
            'company_share_product': not bool(product_rule.active)
        }

    @api.multi
    def set_auth_company_share_product(self):
        self.ensure_one()
        product_rule = self.env.ref('product.product_comp_rule')
        product_rule.write({'active': not bool(self.company_share_product)})
