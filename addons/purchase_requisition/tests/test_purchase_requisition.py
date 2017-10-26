# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo import fields


class TestPurchaseRequisition(common.TransactionCase):

    def setUp(self):
        super(TestPurchaseRequisition, self).setUp()

        self.product_09_id = self.ref('product.product_product_9')
        self.product_09_uom_id = self.ref('product.product_uom_unit')
        self.product_13_id = self.ref('product.product_product_13')
        self.res_partner_1_id = self.ref('base.res_partner_1')
        self.res_company_id = self.ref('base.main_company')

        self.ResUser = self.env['res.users']
        # Create a user as 'Purchase Requisition Manager'
        self.res_users_purchase_requisition_manager = self.ResUser.create({'company_id': self.res_company_id, 'name': 'Purchase requisition Manager', 'login': 'prm', 'email': 'requisition_manager@yourcompany.com'})
        # Added groups for Purchase Requisition Manager.
        self.res_users_purchase_requisition_manager.group_id = self.ref('purchase.group_purchase_manager')
        # Create a user as 'Purchase Requisition User'
        self.res_users_purchase_requisition_user = self.ResUser.create({'company_id': self.res_company_id, 'name': 'Purchase requisition User', 'login': 'pru', 'email': 'requisition_user@yourcompany.com'})
        # Added groups for Purchase Requisition User.
        self.res_users_purchase_requisition_user.group_id = self.ref('purchase.group_purchase_user')

        # In order to test process of the purchase requisition ,create requisition
        self.requisition1 = self.env['purchase.requisition'].create({'line_ids': [(0, 0, {'product_id': self.product_09_id, 'product_qty': 10.0, 'product_uom_id': self.product_09_uom_id})]})

    def test_00_purchase_requisition_users(self):
        self.assertTrue(self.res_users_purchase_requisition_manager, 'Manager Should be created')
        self.assertTrue(self.res_users_purchase_requisition_user, 'User Should be created')

    def test_01_cancel_purchase_requisition(self):
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_cancel()
        # Check requisition after cancelled.
        self.assertEqual(self.requisition1.state, 'cancel', 'Requisition should be in cancelled state.')
        # I reset requisition as "New".
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_draft()
        # I duplicate requisition.
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).copy()

    def test_02_purchase_requisition(self):
        date_planned = fields.Datetime.now()
        warehouse = self.env['stock.warehouse'].browse(self.ref('stock.warehouse0'))
        product = self.env['product.product'].browse(self.product_13_id)
        product.write({'route_ids': [(4, self.ref('purchase.route_warehouse0_buy'))]})
        self.env['procurement.group'].run(product, 14, self.env['product.uom'].browse(self.ref('product.product_uom_unit')), warehouse.lot_stock_id, '/', '/',
                                          {
                                            'warehouse_id': warehouse,
                                            'date_planned': date_planned,
                                          })

        # Check requisition details which created after run procurement.
        line = self.env['purchase.requisition.line'].search([('product_id', '=', self.product_13_id), ('product_qty', '=', 14.0)])
        requisition = line[0].requisition_id
        self.assertEqual(requisition.date_end, date_planned, "End date does not correspond.")
        self.assertEqual(len(requisition.line_ids), 1, "Requisition Lines should be one.")
        self.assertEqual(line.product_uom_id.id, self.ref('product.product_uom_unit'), "UOM is not correspond.")

        # Give access rights of Purchase Requisition User to open requisition
        # Set tender state to choose tendering line.
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_in_progress()
        self.requisition1.sudo(self.res_users_purchase_requisition_user.id).action_open()

        # Vendor send one RFQ so I create a RfQ of that agreement.
        PurchaseOrder = self.env['purchase.order']
        purchase_order = PurchaseOrder.new({'partner_id': self.res_partner_1_id, 'requisition_id': self.requisition1.id})
        purchase_order._onchange_requisition_id()
        po_dict = purchase_order._convert_to_write({name: purchase_order[name] for name in purchase_order._cache})
        self.po_requisition = PurchaseOrder.create(po_dict)
        self.assertEqual(len(self.po_requisition.order_line), 1, 'Purchase order should have one line')

    def test_03_purchase_requisition(self):
        price_product09 = 34
        price_product13 = 62
        quantity = 26
        # Create a pruchase requisition with type blanket order and two product
        line1 = (0, 0, {'product_id': self.product_09_id, 'product_qty': quantity, 'product_uom_id': self.product_09_uom_id, 'price_unit': price_product09})

        self.product_13_uom_id = self.ref('product.product_uom_unit')
        line2 = (0, 0, {'product_id': self.product_13_id, 'product_qty': quantity, 'product_uom_id': self.product_13_uom_id, 'price_unit': price_product13})

        requisition_type = self.env['purchase.requisition.type'].create({'name': 'Blanket test', 'quantity_copy': 'none'})
        self.requisition_blanket = self.env['purchase.requisition'].create({'line_ids': [line1, line2], 'type_id': requisition_type.id, 'vendor_id': self.res_partner_1_id})

        # confirm the requisition
        self.requisition_blanket.action_in_progress()

        # Check for both product that the new supplier info(purchase.requisition.vendor_id) is added to the puchase tab
        # and check the quantity
        seller_partner1 = self.env['res.partner'].browse(self.res_partner_1_id)

        seller09 = self.env['product.product'].browse(self.product_09_id).seller_ids.search([('price', '=', price_product09)]).name
        id09 = self.env['product.product'].browse(self.product_09_id).seller_ids.search([('price', '=', price_product09)]).id
        self.assertEqual(seller09, seller_partner1, 'The supplierinfo is not the good one')

        seller13 = self.env['product.product'].browse(self.product_13_id).seller_ids.search([('price', '=', price_product13)]).name
        id13 = self.env['product.product'].browse(self.product_13_id).seller_ids.search([('price', '=', price_product13)]).id
        self.assertEqual(seller13, seller_partner1, 'The supplierinfo is not the good one')

        # Put the requisition in done Status
        self.requisition_blanket.action_close()

        self.assertFalse(self.env['product.product'].browse(self.product_09_id).seller_ids.search([('id', '=', id09)]), 'The supplier info should be removed')
        self.assertFalse(self.env['product.product'].browse(self.product_13_id).seller_ids.search([('id', '=', id13)]), 'The supplier info should be removed')

    def test_04_purchase_requisition(self):
        # Does a blanket order impact price on a quotation ?

        # Product creation
        unit = self.ref("product.product_uom_unit")
        self.warehouse = self.env.ref('stock.warehouse0')
        route_buy = self.ref('purchase.route_warehouse0_buy')
        route_mto = self.warehouse.mto_pull_id.route_id.id
        self.company1 = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        self.supplierinfo = self.env['product.supplierinfo'].create({
            'name': self.company1.id,
            'price': 50,
        })
        self.product_test = self.env['product.product'].create({
            'name': 'Usb Keyboard',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [self.supplierinfo.id])],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })

        # Stock picking
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        receipt = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': self.company1.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })

        move1 = self.env['stock.move'].create({
            'picking_id': receipt.id,
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_test.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()

        # Verification : there should be a purchase order created with the good price
        self.assertEqual(self.env['purchase.order'].search([('partner_id', '=', self.company1.id)]).order_line.price_unit, 50, 'The price on the purchase order is not the supplierinfo one')

        # Blanket order creation
        line1 = (0, 0, {'product_id': self.product_test.id, 'product_qty': 18, 'product_uom_id': self.product_test.uom_po_id.id, 'price_unit': 42})
        requisition_type = self.env['purchase.requisition.type'].create({'name': 'Blanket test', 'quantity_copy': 'none'})
        self.requisition_blanket = self.env['purchase.requisition'].create({'line_ids': [line1], 'type_id': requisition_type.id, 'vendor_id': self.company1.id})

        # Second stock move
        receipt2 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': self.company1.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })

        move2 = self.env['stock.move'].create({
            'picking_id': receipt2.id,
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_test.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10
        })
        move2._action_confirm()

        # Verifications
        self.assertEqual(self.env['purchase.order'].search([('partner_id', '=', self.company1.id)]).order_line.price_unit, 42, 'The price on the purchase order is not the blanquet order one')
