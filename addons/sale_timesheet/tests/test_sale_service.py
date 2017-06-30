# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.tests.test_sale_common import TestSale


class TestSaleService(TestSale):

    def setUp(self):
        super(TestSaleService, self).setUp()

        # create project
        self.project = self.env['project.project'].create({
            'name': 'Project for selling timesheets',
            'allow_timesheets': True,
            'use_tasks': True,
        })

        # create service products
        self.product_task = self.env['product.product'].create({
            'name': "Service creating a task",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('product.product_uom_hour').id,
            'uom_po_id': self.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI',
            'track_service': 'task',
            'project_id': False,  # project will be created
        })
        self.product_task2 = self.env['product.product'].create({
            'name': "Service creating a task SECOND",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('product.product_uom_hour').id,
            'uom_po_id': self.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI',
            'track_service': 'task',
            'project_id': False,  # project will be created
        })
        self.product_task_with_project = self.env['product.product'].create({
            'name': "Service creating a task in a defined project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('product.product_uom_hour').id,
            'uom_po_id': self.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI',
            'track_service': 'task',
            'project_id': self.project_id.id,
        })
        self.product_project = self.env['product.product'].create({
            'name': "Service creating a project",
            'standard_price': 37,
            'list_price': 51,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.env.ref('product.product_uom_hour').id,
            'uom_po_id': self.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-ORDER',
            'track_service': 'timesheet',
            'project_id': False,  # project will be created
        })

    def test_sale_service(self):
        """ Test task creation when confirming a so with the corresponding product """
        prod_task = self.env.ref('product.product_product_1')
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': prod_task.name, 'product_id': prod_task.id, 'product_uom_qty': 50, 'product_uom': prod_task.uom_id.id, 'price_unit': prod_task.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        so = self.env['sale.order'].create(so_vals)
        so.action_confirm()
        self.assertEqual(so.invoice_status, 'no', 'Sale Service: there should be nothing to invoice after validation')

        # check task creation
        project = self.env.ref('sale_timesheet.project_GAP')
        task = project.task_ids.filtered(lambda t: t.name == '%s:%s' % (so.name, prod_task.name))
        self.assertTrue(task, 'Sale Service: task is not created')
        self.assertEqual(task.partner_id, so.partner_id, 'Sale Service: customer should be the same on task and on SO')
        # register timesheet on task
        self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': project.id,
            'task_id': task.id,
            'unit_amount': 50,
            'user_id': self.manager.id,
        })
        self.assertEqual(so.invoice_status, 'to invoice', 'Sale Service: there should be something to invoice after registering timesheets')
        so.action_invoice_create()
        line = so.order_line
        self.assertTrue(line.product_uom_qty == line.qty_delivered == line.qty_invoiced, 'Sale Service: line should be invoiced completely')
        self.assertEqual(so.invoice_status, 'invoiced', 'Sale Service: SO should be invoiced')

    def test_sale_service_project_task_generation(self):
        """ Test the task and project generation when selling and upselling services """
        # create SO and confirm it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_usd.id,
            'partner_invoice_id': self.partner_usd.id,
            'partner_shipping_id': self.partner_usd.id,
            'pricelist_id': self.pricelist_usd.id,
            'order_line': [
                (0, 0, {
                    'name': 'line1: project',
                    'product_id': self.product_project.id,
                    'product_uom_qty': 50,
                    'product_uom': self.product_project.uom_id.id,
                    'price_unit': self.product_project.list_price,
                }),
                (0, 0, {
                    'name': 'line1: task',
                    'product_id': self.product_task.id,
                    'product_uom_qty': 50,
                    'product_uom': self.product_task.uom_id.id,
                    'price_unit': self.product_task.list_price,
                })
            ],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.project_id, sale_order.tasks_ids[0].project_id.analytic_account_id, "Created task should be in the project of the SO")
        self.assertEqual(sale_order.tasks_count, 1, "A task should have been created on SO confirmation")

        # upsell the SO by adding a product creating a task in a given project, and a product without speficied project
        so_line3 = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': 'line3: upsell task without project',
            'product_id': self.product_task2.id,
            'product_uom_qty': 22,
            'product_uom': self.product_task2.uom_id.id,
            'price_unit': self.product_task2.list_price,
        })
        so_line4 = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': 'line4: upsell task with project',
            'product_id': self.product_project.id,
            'product_uom_qty': 11,
            'product_uom': self.product_project.uom_id.id,
            'price_unit': self.product_project.list_price,
        })

        task_line3 = self.env['project.task'].search([('sale_line_id', '=', so_line3.id)])
        task_line4 = self.env['project.task'].search([('sale_line_id', '=', so_line4.id)])

        self.assertEqual(sale_order.tasks_count, 2, "A second task should have been created and linked to the SO line")
        self.assertEqual(len(task_line3), 1, "SO line3 should have only one task")
        self.assertEqual(len(task_line4), 1, "SO line4 should have only one task")

        self.assertEqual(task_line3.project_id, sale_order.projet_project_id, "The task from SO line3 should be in the project of the SO")
        self.assertEqual(task_line4.project_id, self.product_task_with_project, "The task from SO line4 should be in the project configured on the product")
