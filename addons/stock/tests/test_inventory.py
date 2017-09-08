# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase


class TestInventory(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestInventory, cls).setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.uom_unit = cls.env.ref('product.product_uom_unit')
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

    def test_inventory_1(self):
        """ Check that making an inventory adjustment to remove all products from stock is working
        as expected.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 100)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 100.0)

        # remove them with an inventory adjustment
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
        })
        inventory.prepare_inventory()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 100)
        inventory.line_ids.product_qty = 0  # Put the quantity back to 0
        inventory.action_done()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)

    def test_inventory_2(self):
        """ Check that adding a tracked product through an inventory adjustment work as expected.
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'exhausted': True,  # should be set by an onchange
        })
        inventory.prepare_inventory()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })

        inventory.line_ids.prod_lot_id = lot1
        inventory.line_ids.product_qty = 1

        inventory.action_done()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1)), 1.0)
        self.assertEqual(lot1.product_qty, 1.0)

    def test_inventory_3(self):
        """ Check that it's not posisble to have multiple products with a serial number through an
        inventory adjustment
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'exhausted': True,  # should be set by an onchange
        })
        inventory.prepare_inventory()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })

        inventory.line_ids.prod_lot_id = lot1
        inventory.line_ids.product_qty = 2

        with self.assertRaises(ValidationError):
            inventory.action_done()

    def test_inventory_4(self):
        """ Check that even if a product is tracked by serial number, it's possible to add
        untracked one in an inventory adjustment.
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'exhausted': True,  # should be set by an onchange
        })
        inventory.prepare_inventory()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })

        inventory.line_ids.prod_lot_id = lot1
        inventory.line_ids.product_qty = 1

        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': self.product2.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 10,
            'location_id': self.stock_location.id,
        })
        inventory.action_done()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, strict=True), 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 11.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location)), 2.0)

    def test_inventory_5(self):
        """ Check that assigning an owner does work.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_inventory_5'})

        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
            'exhausted': True,
        })
        inventory.prepare_inventory()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)
        inventory.line_ids.partner_id = owner1
        inventory.line_ids.product_qty = 5
        inventory.action_done()

        quant = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quant), 1)
        self.assertEqual(quant.quantity, 5)
        self.assertEqual(quant.owner_id.id, owner1.id)
