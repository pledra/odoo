# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Bridge Extend Address',
    'version': '1.0',
    'category': 'Point Of Sale',
    'sequence': 20,
    'summary': 'Bridge module to add the fields of base_address_extended in the pos',
    'description': "",
    'depends': ['point_of_sale', 'base_address_extended'],
    'installable': True,
    'application': False,
    'autoinstall': True,

    'data': ['views/pos_base_address_extended_views.xml'],

    'qweb': ['static/src/xml/pos.xml'],
    'website': 'https://www.odoo.com/page/point-of-sale',
}
