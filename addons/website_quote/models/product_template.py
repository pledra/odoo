# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.translate import html_translate


class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_description = fields.Html('Description for the website', sanitize=False) # hack, if website_sale is not installed
    quote_description = fields.Html('Description for the quote', sanitize=False, translate=html_translate)
