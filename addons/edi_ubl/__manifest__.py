# -*- coding: utf-8 -*-
{
    'name': 'UBL',
    'version': '0.1',
    'category': 'Hidden',
    'summary': 'Universal Business Language (UBL)',
    'description': """
This is the base module for the implementation of the `Universal Business Language (UBL)
<http://ubl.xml.org/>`_ standard.  The UBL standard became the `ISO/IEC 19845 
<http://www.iso.org/iso/catalogue_detail.htm?csnumber=66370>`_ standard in January 2016 
(cf the `official announce <http://www.prweb.com/releases/2016/01/prweb13186919.htm>`_).
    """,
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/unece/unece_agencies.xml',
        'data/unece/unece_code_types.xml',
        'data/unece/unece_code_taxes.xml',
        'data/unece/unece_code_categories.xml',
        'data/unece/unece_code_payment_means.xml',
        'views/account_tax_view.xml',
        'views/account_invoice_view.xml',
        'views/ubl_cac_2_1.xml',
        'views/ubl_invoice_2_1.xml',
    ],
    'installable': True,
    'auto_install': False,
}