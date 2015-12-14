{
    'name': 'Online Proposals Sections',
    'category': 'Sale',
    'summary': 'Online Proposals Sale Layout, page-break, subtotals, separators, report',
    'website': 'https://www.odoo.com/page/quote-builder',
    'version': '1.0',
    'sequence': 14,
    'description': """
Manage your sales reports
=========================
With this module you can personnalize the sale order templates report with
separators, page-breaks or subtotals.
    """,
    'depends': ['website_quote', 'sale_layout'],
    'data': [
        'views/sale_layout_category_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}
