# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_policy = fields.Selection([
        ('ordered_timesheet', 'Ordered Quantities'),
        ('delivered_timesheet', 'Timesheets on tasks'),
        ('delivered_manual', 'Milesones')
    ], string="Invoice based on", compute='_compute_service_policy', inverse='_inverse_service_policy')
    service_type = fields.Selection(selection_add=[
        ('timesheet', 'Timesheets on project (one fare per SO/Project)'),
    ])
    service_tracking = fields.Selection([
        ('no', 'Don\'t create task'),
        ('task_global_project', 'Create task in global Project'),
        ('task_new_project', 'Create task in new project'),
        ('project_only', 'Create Project but not task'),
    ], string="Service Tracking", default="no", help="UPDATE ME TODO JEM")
    project_id = fields.Many2one(
        'project.project', 'Project', company_dependent=True,
        help='Create a task under this project on sales order validation. This setting must be set for each company.')

    @api.depends('invoice_policy', 'service_type')
    def _compute_service_policy(self):
        for product in self:
            policy = False
            if product.invoice_policy == 'order' and product.service_type == 'timesheet':
                policy = 'ordered_timesheet'
            if product.invoice_policy == 'delivery':
                policy = 'delivered_manual' if product.service_type == 'manual' else 'delivered_timesheet'
            product.service_policy = policy

    def _inverse_service_policy(self):
        for product in self:
            if product.service_policy == 'ordered_timesheet':
                product.invoice_policy = 'order'
                product.service_type = 'manual'
            else:
                product.invoice_policy = 'delivery'
                product.service_type = 'manual' if product.service_policy == 'delivered_manual' else 'timesheet'

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'service':
            self.service_type = 'timesheet'
        else:
            self.service_type = 'manual'


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _need_procurement(self):
        for product in self:
            if product.type == 'service' and product.service_type == 'timesheet' and product.service_tracking != 'no':
                return True
        return super(ProductProduct, self)._need_procurement()
