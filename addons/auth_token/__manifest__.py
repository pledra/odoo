# -*- coding: utf-8 -*-
{
    'name': 'Token-based Authentication',
    'version': '1.0',
    'category': 'Extra Tools',
    'description': """
This module allows an Administrator to invite someone to assist them (via link or email) without having
to share/modify their credentials.
""",
    'website': 'http://odoo.com',
    'depends': [
        'web', 'base_setup', 'web_settings_dashboard', 'mail'
    ],
    'data': [
        'views/auth_token_views.xml',
        'views/auth_token_templates.xml',
        'data/auth_token_data.xml',
        'security/ir.model.access.csv'
    ],
    'qweb': ['static/src/xml/dashboard_templates.xml'],
    'installable': True,
}
