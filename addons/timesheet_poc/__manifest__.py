# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Timesheets',
    'version': '1.0',
    'category': 'Services',
    'sequence': 99,
    'summary': 'SUMMARY',
    'description': """
DESCRIPTION
===========
    """,
    'depends': [
        'resource',
        'analytic',
    ],
    'data': [
        'views/account_analytic_line_views.xml',
        'views/work_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
