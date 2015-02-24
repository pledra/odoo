# -*- coding: utf-8 -*-

{
    'name': 'Account Analytic Defaults',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
Set default values for your analytic accounts.
==============================================

Allows to automatically select analytic accounts based on criterions:
---------------------------------------------------------------------
    * Product
    * Partner
    * User
    * Company
    * Date
    """,
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['sale_stock'],
    'data': [
        'security/ir.model.access.csv', 
        'security/account_analytic_default_security.xml', 
        'account_analytic_default_view.xml'
    ],
    'demo': [],
    'installable': True,
}
