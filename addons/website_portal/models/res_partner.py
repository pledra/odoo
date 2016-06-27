# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models, fields
from openerp.osv.orm import browse_record


class res_partner(models.Model):
    _inherit = 'res.partner'

    website_company_name = fields.Char('Company Name (eCommerce)')

    @api.multi
    def create_company(self):
        self.ensure_one()
        if self.website_company_name:
            fields = ['street', 'street2', 'zip', 'city', 'state_id', 'country_id', 'website']

            # move info from partner to company
            values = dict(name=self.website_company_name)
            self.website_company_name = False
            for f in fields:
                values[f] = isinstance(self[f], browse_record) and self[f].id or self[f]
                self[f] = False
            new_company = self.create(values)
            self.parent_id = new_company
            for child in self.child_ids:
                child.parent_id = new_company
        return True

    @api.multi
    def create_company(self, vals):
        if vals.get('parent_id'):
            vals['website_company_name'] = False