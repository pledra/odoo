from openerp.osv import osv, fields


class sale_quote_template(osv.osv):
    _inherit = 'sale.quote.line'

    _order = 'categ_sequence, sale_layout_cat_id, sequence, id'

    _columns = {
        'sale_layout_cat_id': fields.many2one('sale_layout.category',
                                              string='Section'),
        'categ_sequence': fields.related('sale_layout_cat_id',
                                         'sequence', type='integer',
                                         string='Layout Sequence',)
    }
