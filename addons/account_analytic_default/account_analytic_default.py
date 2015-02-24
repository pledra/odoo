# -*- coding: utf-8 -*-

from openerp import api, fields, models


class AccountAnalyticDefault(models.Model):

    _name = "account.analytic.default"
    _description = "Analytic Distribution"
    _rec_name = "analytic_id"
    _order = "sequence"


    sequence = fields.Integer(default=0, help="Gives the sequence order when displaying a list of analytic distribution")
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade', help="Select a partner which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)")
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', help="Select a user which will use analytic account specified in analytic default.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)")
    date_start = fields.Date(string='Start Date', help="Default start date for this Analytic Account.")
    date_stop = fields.Date(string='End Date', help="Default end date for this Analytic Account.")

    @api.model
    def account_get(self, product_id=None, partner_id=None, user_id=None, date=None, company_id=None):
        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
        domain += [('product_id', '=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
        domain += [('partner_id', '=', False)]
        if company_id:
            domain += ['|', ('company_id', '=', company_id)]
        domain += [('company_id', '=', False)]
        if user_id:
            domain += ['|', ('user_id', '=', user_id)]
        domain += [('user_id', '=', False)]
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        best_index = -1
        res = False
        for rec in self.search(domain):
            index = 0
            if rec.product_id: index += 1
            if rec.partner_id: index += 1
            if rec.company_id: index += 1
            if rec.user_id: index += 1
            if rec.date_start: index += 1
            if rec.date_stop: index += 1
            if index > best_index:
                res = rec
                best_index = index
        return res


class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"
    _description = "Invoice Line"

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, company_id=None):
        res_prod = super(account_invoice_line, self).product_id_change(product, uom_id, qty, name, type, partner_id, fposition_id, price_unit, currency_id=currency_id, company_id=company_id)
        rec = self.env['account.analytic.default'].account_get(product, partner_id, self.env.uid, fields.Date.context_today(self), company_id)
        res_prod['value']['account_analytic_id'] = rec and rec.analytic_id.id
        return res_prod


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def invoice_line_create(self):
        create_ids = super(sale_order_line, self).invoice_line_create()
        if not self.ids:
            return create_ids
        for line in self.env['account.invoice.line'].browse(create_ids):
            rec = self.env['account.analytic.default'].account_get(line.product_id.id, self.order_id.partner_id.id, self.order_id.user_id.id, fields.Date.context_today(self), self.order_id.company_id.id)
            if rec:
                line.write({'account_analytic_id': rec.analytic_id.id})
        return create_ids


class product_product(models.Model):
    _inherit = 'product.product'

    @api.multi
    @api.depends('rules_count')
    def _rules_count(self):
        AccountAnalyticDefault = self.env['account.analytic.default']
        for record in self:
            record.rules_count = AccountAnalyticDefault.search_count([('product_id', '=', record.id)])

    rules_count = fields.Integer(compute='_rules_count', string='# Analytic Rules')


class product_template(models.Model):
    _inherit = 'product.template'

    @api.multi
    @api.depends('product_variant_ids.rules_count')
    def _rules_count(self):
        for product_tmpl_id in self:
            product_tmpl_id.rules_count = sum([p.rules_count for p in product_tmpl_id.product_variant_ids])

    rules_count = fields.Integer(compute='_rules_count', string='# Analytic Rules')

    @api.multi
    def action_view_rules(self):
        products = self._get_products()
        result = self._get_act_window_dict('account_analytic_default.action_product_default_list')
        result['domain'] = "[('product_id', 'in', [" + ','.join(map(str, products)) + "])]"
        result['context'] = "{}"
        # Remove context so it is not going to filter on product_id with active_id of template
        return result
