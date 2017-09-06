# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestSale
from odoo.exceptions import UserError


# class TestSaleStock(TestSale):
#     def test_00_sale_stock_invoice(self):
#         """
#         Test SO's changes when playing around with stock moves, quants, pack operations, pickings
#         and whatever other model there is in stock with "invoice on delivery" products
#         """
#         inv_obj = self.env['account.invoice']
#         self.so = self.env['sale.order'].create({
#             'partner_id': self.partner.id,
#             'partner_invoice_id': self.partner.id,
#             'partner_shipping_id': self.partner.id,
#             'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for p in self.products.values()],
#             'pricelist_id': self.env.ref('product.list0').id,
#             'picking_policy': 'direct',
#         })
#
#         # confirm our standard so, check the picking
#         self.so.action_confirm()
#         self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" stockable products')
#         # invoice on order
#         self.so.action_invoice_create()
#
#         # deliver partially, check the so's invoice_status and delivered quantities
#         self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "nothing to invoice" after invoicing')
#         pick = self.so.picking_ids
#         pick.force_assign()
#         pick.move_lines.write({'quantity_done': 1})
#         wiz_act = pick.button_validate()
#         wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
#         wiz.process()
#         self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" after partial delivery')
#         del_qties = [sol.qty_delivered for sol in self.so.order_line]
#         del_qties_truth = [1.0 if sol.product_id.type in ['product', 'consu'] else 0.0 for sol in self.so.order_line]
#         self.assertEqual(del_qties, del_qties_truth, 'Sale Stock: delivered quantities are wrong after partial delivery')
#         # invoice on delivery: only stockable products
#         inv_id = self.so.action_invoice_create()
#         inv_1 = inv_obj.browse(inv_id)
#         self.assertTrue(all([il.product_id.invoice_policy == 'delivery' for il in inv_1.invoice_line_ids]),
#                         'Sale Stock: invoice should only contain "invoice on delivery" products')
#
#         # complete the delivery and check invoice_status again
#         self.assertEqual(self.so.invoice_status, 'no',
#                          'Sale Stock: so invoice_status should be "nothing to invoice" after partial delivery and invoicing')
#         self.assertEqual(len(self.so.picking_ids), 2, 'Sale Stock: number of pickings should be 2')
#         pick_2 = self.so.picking_ids[0]
#         pick_2.force_assign()
#         pick_2.move_lines.write({'quantity_done': 1})
#         self.assertIsNone(pick_2.button_validate(), 'Sale Stock: second picking should be final without need for a backorder')
#         self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" after complete delivery')
#         del_qties = [sol.qty_delivered for sol in self.so.order_line]
#         del_qties_truth = [2.0 if sol.product_id.type in ['product', 'consu'] else 0.0 for sol in self.so.order_line]
#         self.assertEqual(del_qties, del_qties_truth, 'Sale Stock: delivered quantities are wrong after complete delivery')
#         # Without timesheet, we manually set the delivered qty for the product serv_del
#         self.so.order_line[1]['qty_delivered'] = 2.0
#         inv_id = self.so.action_invoice_create()
#         self.assertEqual(self.so.invoice_status, 'invoiced',
#                          'Sale Stock: so invoice_status should be "fully invoiced" after complete delivery and invoicing')
#
#     def test_01_sale_stock_order(self):
#         """
#         Test SO's changes when playing around with stock moves, quants, pack operations, pickings
#         and whatever other model there is in stock with "invoice on order" products
#         """
#         # let's cheat and put all our products to "invoice on order"
#         self.so = self.env['sale.order'].create({
#             'partner_id': self.partner.id,
#             'partner_invoice_id': self.partner.id,
#             'partner_shipping_id': self.partner.id,
#             'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for p in self.products.values()],
#             'pricelist_id': self.env.ref('product.list0').id,
#             'picking_policy': 'direct',
#         })
#         for sol in self.so.order_line:
#             sol.product_id.invoice_policy = 'order'
#         # confirm our standard so, check the picking
#         self.so.action_confirm()
#         self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on order" stockable products')
#         # let's do an invoice for a deposit of 5%
#         adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
#             'advance_payment_method': 'percentage',
#             'amount': 5.0,
#             'product_id': self.env.ref('sale.advance_product_0').id,
#         })
#         act = adv_wiz.with_context(open_invoices=True).create_invoices()
#         inv = self.env['account.invoice'].browse(act['res_id'])
#         self.assertEqual(inv.amount_untaxed, self.so.amount_untaxed * 5.0 / 100.0, 'Sale Stock: deposit invoice is wrong')
#         self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so should be to invoice after invoicing deposit')
#         # invoice on order: everything should be invoiced
#         self.so.action_invoice_create(final=True)
#         self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so should be fully invoiced after second invoice')
#
#         # deliver, check the delivered quantities
#         pick = self.so.picking_ids
#         pick.force_assign()
#         pick.move_lines.write({'quantity_done': 2})
#         self.assertIsNone(pick.button_validate(), 'Sale Stock: complete delivery should not need a backorder')
#         del_qties = [sol.qty_delivered for sol in self.so.order_line]
#         del_qties_truth = [2.0 if sol.product_id.type in ['product', 'consu'] else 0.0 for sol in self.so.order_line]
#         self.assertEqual(del_qties, del_qties_truth, 'Sale Stock: delivered quantities are wrong after partial delivery')
#         # invoice on delivery: nothing to invoice
#         with self.assertRaises(UserError):
#             self.so.action_invoice_create()
#
#     def test_02_sale_stock_return(self):
#         """
#         Test a SO with a product invoiced on delivery. Deliver and invoice the SO, then do a return
#         of the picking. Check that a refund invoice is well generated.
#         """
#         # intial so
#         self.partner = self.env.ref('base.res_partner_1')
#         self.product = self.env.ref('product.product_delivery_01')
#         so_vals = {
#             'partner_id': self.partner.id,
#             'partner_invoice_id': self.partner.id,
#             'partner_shipping_id': self.partner.id,
#             'order_line': [(0, 0, {
#                 'name': self.product.name,
#                 'product_id': self.product.id,
#                 'product_uom_qty': 5.0,
#                 'product_uom': self.product.uom_id.id,
#                 'price_unit': self.product.list_price})],
#             'pricelist_id': self.env.ref('product.list0').id,
#         }
#         self.so = self.env['sale.order'].create(so_vals)
#
#         # confirm our standard so, check the picking
#         self.so.action_confirm()
#         self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" stockable products')
#
#         # invoice in on delivery, nothing should be invoiced
#         self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" instead of "%s".' % self.so.invoice_status)
#
#         # deliver completely
#         pick = self.so.picking_ids
#         pick.force_assign()
#         pick.move_lines.write({'quantity_done': 5})
#         pick.do_new_transfer()
#
#         # Check quantity delivered
#         del_qty = sum(sol.qty_delivered for sol in self.so.order_line)
#         self.assertEqual(del_qty, 5.0, 'Sale Stock: delivered quantity should be 5.0 instead of %s after complete delivery' % del_qty)
#
#         # Check invoice
#         self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" instead of "%s" before invoicing' % self.so.invoice_status)
#         inv_1_id = self.so.action_invoice_create()
#         self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so invoice_status should be "invoiced" instead of "%s" after invoicing' % self.so.invoice_status)
#         self.assertEqual(len(inv_1_id), 1, 'Sale Stock: only one invoice instead of "%s" should be created' % len(inv_1_id))
#         self.inv_1 = self.env['account.invoice'].browse(inv_1_id)
#         self.assertEqual(self.inv_1.amount_untaxed, self.inv_1.amount_untaxed, 'Sale Stock: amount in SO and invoice should be the same')
#         self.inv_1.action_invoice_open()
#
#         # Create return picking
#         StockReturnPicking = self.env['stock.return.picking']
#         default_data = StockReturnPicking.with_context(active_ids=pick.ids, active_id=pick.ids[0]).default_get(['move_dest_exists', 'original_location_id', 'product_return_moves', 'parent_location_id', 'location_id'])
#         return_wiz = StockReturnPicking.with_context(active_ids=pick.ids, active_id=pick.ids[0]).create(default_data)
#         return_wiz.product_return_moves.quantity = 2.0 # Return only 2
#         return_wiz.product_return_moves.to_refund = True # Refund these 2
#         res = return_wiz.create_returns()
#         return_pick = self.env['stock.picking'].browse(res['res_id'])
#
#         # Validate picking
#         return_pick.force_assign()
#         return_pick.move_lines.write({'quantity_done': 2})
#         return_pick.do_new_transfer()
#
#         # Check invoice
#         self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" instead of "%s" after picking return' % self.so.invoice_status)
#         self.assertEqual(self.so.order_line[0].qty_delivered, 3.0, 'Sale Stock: delivered quantity should be 3.0 instead of "%s" after picking return' % self.so.order_line[0].qty_delivered)
#         # let's do an invoice with refunds
#         adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
#             'advance_payment_method': 'all',
#         })
#         adv_wiz.with_context(open_invoices=True).create_invoices()
#         self.inv_2 = self.so.invoice_ids.filtered(lambda r: r.state == 'draft')
#         self.assertEqual(self.inv_2.invoice_line_ids[0].quantity, 2.0, 'Sale Stock: refund quantity on the invoice should be 2.0 instead of "%s".' % self.inv_2.invoice_line_ids[0].quantity)
#         self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" instead of "%s" after invoicing the return' % self.so.invoice_status)
#
#     def test_03_sale_stock_delivery_partial(self):
#         """
#         Test a SO with a product invoiced on delivery. Deliver partially and invoice the SO, when
#         the SO is set on 'done', the SO should be fully invoiced.
#         """
#         # intial so
#         self.partner = self.env.ref('base.res_partner_1')
#         self.product = self.env.ref('product.product_delivery_01')
#         so_vals = {
#             'partner_id': self.partner.id,
#             'partner_invoice_id': self.partner.id,
#             'partner_shipping_id': self.partner.id,
#             'order_line': [(0, 0, {
#                 'name': self.product.name,
#                 'product_id': self.product.id,
#                 'product_uom_qty': 5.0,
#                 'product_uom': self.product.uom_id.id,
#                 'price_unit': self.product.list_price})],
#             'pricelist_id': self.env.ref('product.list0').id,
#         }
#         self.so = self.env['sale.order'].create(so_vals)
#
#         # confirm our standard so, check the picking
#         self.so.action_confirm()
#         self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" stockable products')
#
#         # invoice in on delivery, nothing should be invoiced
#         self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "nothing to invoice"')
#
#         # deliver partially
#         pick = self.so.picking_ids
#         pick.force_assign()
#         pick.move_lines.write({'quantity_done': 4})
#         res_dict = pick.button_validate()
#         wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
#         wizard.process_cancel_backorder()
#
#         # Check quantity delivered
#         del_qty = sum(sol.qty_delivered for sol in self.so.order_line)
#         self.assertEqual(del_qty, 4.0, 'Sale Stock: delivered quantity should be 4.0 after partial delivery')
#
#         # Check invoice
#         self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" before invoicing')
#         inv_1_id = self.so.action_invoice_create()
#         self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" after invoicing')
#         self.assertEqual(len(inv_1_id), 1, 'Sale Stock: only one invoice should be created')
#         self.inv_1 = self.env['account.invoice'].browse(inv_1_id)
#         self.assertEqual(self.inv_1.amount_untaxed, self.inv_1.amount_untaxed, 'Sale Stock: amount in SO and invoice should be the same')
#
#         self.so.action_done()
#         self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so invoice_status should be "invoiced" when set to done')
#
#     def test_04_create_picking_update_saleorderline(self):
#         """
#         Test that updating multiple sale order lines after a succesful delivery creates a single picking containing
#         the new move lines.
#         """
#         # sell two products
#         item1 = self.products['prod_order']
#         item2 = self.products['prod_del']
#
#         self.so = self.env['sale.order'].create({
#             'partner_id': self.partner.id,
#             'order_line': [
#                 (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
#                 (0, 0, {'name': item2.name, 'product_id': item2.id, 'product_uom_qty': 1, 'product_uom': item2.uom_id.id, 'price_unit': item2.list_price}),
#             ],
#         })
#         self.so.action_confirm()
#
#         # deliver them
#         self.assertEquals(len(self.so.picking_ids), 1)
#         self.so.picking_ids[0].force_assign()
#         res_dict = self.so.picking_ids[0].button_validate()
#         wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
#         wizard.process()
#         self.assertEquals(self.so.picking_ids[0].state, "done")
#
#         # update the two original sale order lines
#         self.so.write({
#             'order_line': [
#                 (1, self.so.order_line[0].id, {'product_uom_qty': 2}),
#                 (1, self.so.order_line[1].id, {'product_uom_qty': 2}),
#             ]
#         })
#
#         # a single picking should be created for the new delivery
#         self.assertEquals(len(self.so.picking_ids), 2)


class TestSaleStockValuation(TestSale):
    def setUp(self):
        super(TestSaleStockValuation, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('product.product_uom_unit')

    def _make_receipts(self, product):
        # receive 10@10, 10@15
        move1 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1.action_done()

        move2 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 15.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 15.0,
        })
        move2.action_confirm()
        move2.action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2.action_done()

    def _get_expense_aml(self, product):
        return self.env['account.move.line'].search([
            ('product_id', '=', product.id),
            ('account_id', '=', product.categ_id.property_account_expense_categ_id.id),
        ], order='date, id', limit=1)

    def test_anglo_saxon_fifo_perpetual_order_policy_1(self):
        prod_del = self.products['prod_del']
        prod_del.product_tmpl_id.cost_method = 'fifo'
        prod_del.product_tmpl_id.categ_id.property_valuation = 'real_time'
        prod_del.invoice_policy = 'order'

        prod_del.product_tmpl_id.standard_price = 15

        self._make_receipts(prod_del)

        # sell 15 units
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 15, 'product_uom': p.uom_id.id}) for p in prod_del],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        self.so.action_confirm()

        # don't delivery anything

        # create and open the invoice
        inv = self.so.action_invoice_create()
        inv = self.env['account.invoice'].browse(inv[0])
        inv.action_invoice_open()

        # value to standard price
        aml = self._get_expense_aml(prod_del)
        self.assertEqual(aml.debit, 225.0)

    def test_anglo_saxon_fifo_perpetual_order_policy_2(self):
        prod_del = self.products['prod_del']
        prod_del.product_tmpl_id.cost_method = 'fifo'
        prod_del.product_tmpl_id.categ_id.property_valuation = 'real_time'
        prod_del.invoice_policy = 'order'

        self._make_receipts(prod_del)

        # sell 15 units
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 15, 'product_uom': p.uom_id.id}) for p in prod_del],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        self.so.action_confirm()

        # deliver 15 units
        self.so.picking_ids.move_lines.quantity_done = 15
        self.so.picking_ids.button_validate()

        # create and open the invoice
        inv = self.so.action_invoice_create()
        inv = self.env['account.invoice'].browse(inv[0])
        inv.action_invoice_open()

        # even if the invoice policy is order, we consider the value we actually delivered
        aml = self._get_expense_aml(prod_del)
        self.assertEqual(aml.debit, 175.0)

    def test_anglo_saxon_fifo_perpetual_order_policy_3(self):
        prod_del = self.products['prod_del']
        prod_del.product_tmpl_id.cost_method = 'fifo'
        prod_del.product_tmpl_id.categ_id.property_valuation = 'real_time'
        prod_del.invoice_policy = 'order'

        self._make_receipts(prod_del)

        # sell 10 units
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 15, 'product_uom': p.uom_id.id}) for p in prod_del],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        self.so.action_confirm()

        # deliver 10 units
        self.so.picking_ids.move_lines.quantity_done = 10
        res_dict = self.so.picking_ids.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # create and open the invoice
        inv = self.so.action_invoice_create()
        inv = self.env['account.invoice'].browse(inv[0])
        inv.action_invoice_open()

        # even if the invoice policy is order, we value the delivered quantities at the real value
        # and the non delivered ones at the standard price (that should be updated to 10 following
        # the previous delivery).
        aml = self._get_expense_aml(prod_del)
        self.assertEqual(aml.debit, 150.0)

    def test_anglo_saxon_fifo_perpetual_order_policy_4(self):
        prod_del = self.products['prod_del']
        prod_del.product_tmpl_id.cost_method = 'fifo'
        prod_del.product_tmpl_id.categ_id.property_valuation = 'real_time'
        prod_del.invoice_policy = 'order'

        self._make_receipts(prod_del)

        # sell 10 units
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 15, 'product_uom': p.uom_id.id}) for p in prod_del],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        self.so.action_confirm()

        # deliver 11 units
        self.so.picking_ids.move_lines.quantity_done = 11
        res_dict = self.so.picking_ids.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # create and open the invoice
        inv = self.so.action_invoice_create()
        inv = self.env['account.invoice'].browse(inv[0])
        inv.action_invoice_open()

        # even if the invoice policy is order, we value the delivered quantities at the real value
        # and the non delivered ones at the standard price (that should be updated to 15 following
        # the previous delivery).
        aml = self._get_expense_aml(prod_del)
        self.assertEqual(aml.debit, 175.0)
