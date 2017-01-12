# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheets',
    'version': '1.0',
    'category': 'Not Sure',
    'sequence': 99,
    'summary': 'UPDATE ME',
    'description': """
UPDATE ME
    """,
    'depends': [
        'analytic',
        'work_resource',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/timesheet_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
}
