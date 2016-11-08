# -*- coding: utf-8 -*-
{
    'name': 'Base EDI',
    'version': '0.1',
    'category': 'Hidden',
    'summary': 'Electronic Data Interchange (EDI)',
    'description': """
Electronic Data Interchange (EDI) is an electronic communication method 
that provides standards for exchanging data via any electronic means.
    """,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}