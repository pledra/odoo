# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    task_id = fields.Many2one('project.task', 'Task', copy=False)
    is_service = fields.Boolean("Is service", compute='_compute_is_service', help="Procurement should generate a task and/or a project, depending on the product settings.")

    @api.multi
    @api.depends('product_id', 'product_id.type', 'product_id.service_type', 'product_id.invoice_policy')
    def _compute_is_service(self):
        for procurement in self:
            procurement.is_service = procurement.product_id.type == 'service' and procurement.product_id.service_policy

    @api.multi
    def _assign(self):
        self.ensure_one()
        res = super(ProcurementOrder, self)._assign()
        if not res:
            # if there isn't any specific procurement.rule defined for the product, we may want to create a task
            return self.is_service
        return res

    @api.multi
    def _run(self):
        self.ensure_one()
        if self.is_service:
            # create task
            if self.product_id.service_tracking == 'task_global_project':
                return self._timesheet_find_task()[self.id]
            # create project
            if self.product_id.service_tracking == 'project_only':
                return self._timesheet_find_project()
            # create project and task
            if self.product_id.service_tracking == 'task_new_project':
                return self._timesheet_find_task()[self.id]
            return False  # case of no task creation
        return super(ProcurementOrder, self)._run()

    ####################################################################
    # Services Business
    ####################################################################

    def _convert_qty_company_hours(self):
        company_time_uom_id = self.env.user.company_id.project_time_mode_id
        if self.product_uom.id != company_time_uom_id.id and self.product_uom.category_id.id == company_time_uom_id.category_id.id:
            planned_hours = self.product_uom._compute_quantity(self.product_qty, company_time_uom_id)
        else:
            planned_hours = self.product_qty
        return planned_hours

    def _timesheet_find_project(self):
        """ Determine the service project of the procurement: take the one from the product. If not
            set, take the one from the SO, or create it.
        """
        Project = self.env['project.project']
        project = self.product_id.with_context(force_company=self.company_id.id).project_id
        if not project and self.sale_line_id:
            # find the project corresponding to the analytic account of the sales order
            account = self.sale_line_id.order_id.analytic_account_id
            if not account:
                self.sale_line_id.order_id._create_analytic_account()
                account = self.sale_line_id.order_id.analytic_account_id
            project = Project.search([('analytic_account_id', '=', account.id)], limit=1)
            if not project:
                project_id = account.project_create({'name': account.name, 'use_tasks': True})
                project = Project.browse(project_id)
        return project

    def _timesheet_create_task_prepare_values(self):
        """ Prepare task values from the current procurement """
        self.ensure_one()
        project = self._timesheet_find_project()
        planned_hours = self._convert_qty_company_hours()
        return {
            'name': '%s:%s' % (self.origin or '', self.product_id.name),
            'date_deadline': self.date_planned,
            'planned_hours': planned_hours,
            'remaining_hours': planned_hours,
            'partner_id': self.sale_line_id.order_id.partner_id.id or self.partner_dest_id.id,
            'user_id': self.env.uid,
            'procurement_id': self.id,
            'description': self.name + '<br/>',
            'project_id': project.id,
            'company_id': self.company_id.id,
        }

    @api.multi
    def _timesheet_create_task(self):
        """ Generate task for the given procurements, and link it.

            :return a mapping with the procurement id and its linked task
            :rtype dict
        """
        result = {}
        for procurement in self:
            values = procurement._timesheet_create_task_prepare_values()
            task = self.env['project.task'].create(values)
            procurement.write({'task_id': task.id})

            msg_body = _("Task Created (%s): <a href=# data-oe-model=project.task data-oe-id=%d>%s</a>") % (procurement.product_id.name, task.id, task.name)
            procurement.message_post(body=msg_body)

            if procurement.sale_line_id.order_id:
                procurement.sale_line_id.order_id.message_post(body=msg_body)
                task_msg = _("This task has been created from: <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a> (%s)") % (self.sale_line_id.order_id.id, self.sale_line_id.order_id.name, self.product_id.name)
                task.message_post(body=task_msg)
            result[procurement.id] = task
        return result

    @api.multi
    def _timesheet_find_task(self):
        """ Find the task generated by the procurement. If no task linked, it will be
            created automatically.

            :return a mapping with the procurement id and its linked task
            :rtype dict
        """
        # one search for all procurements
        so_line_ids = self.filtered(lambda proc: proc.sale_line_id).mapped('sale_line_id').ids
        tasks = self.env['project.task'].search([('sale_line_id', 'in', so_line_ids)])
        task_sol_mapping = {task.sale_line_id.id: task for task in tasks}

        result = {}
        for procurement in self:
            task = None
            # If the SO was confirmed, cancelled, set to draft then confirmed, avoid creating a new task.
            if procurement.sale_line_id:
                task = task_sol_mapping.get(procurement.sale_line_id.id)
            # If not found, create one task for the so line
            if not task:
                task = procurement._timesheet_create_task()[procurement.id]
            result[procurement.id] = task
        return result
