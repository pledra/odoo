from openerp.osv import osv


class sale_order(osv.osv):
    _inherit = 'sale.order'

    def onchange_template_id(self, cr, uid, ids, template_id, partner=False, fiscal_position_id=False, pricelist_id=False, context=None):
        res = super(sale_order, self).onchange_template_id(cr, uid, ids, template_id, partner=partner, fiscal_position_id=fiscal_position_id, pricelist_id=pricelist_id, context=context)
        if res.get('value') and res['value'].get('order_line'):
            quote_template = self.pool.get('sale.quote.template').browse(cr, uid, template_id, context=context)
            order_lines = [line[2] for line in res['value']['order_line'] if len(line) == 3 and line[0] == 0]
            for index in range(len(order_lines)):
                order_lines[index]['sale_layout_cat_id'] = quote_template.quote_line[index].sale_layout_cat_id.id
        return res
