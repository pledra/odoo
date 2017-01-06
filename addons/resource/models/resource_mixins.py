# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WorkLogger(models.Model):
    _name = 'work.logger'
    _description = 'Work Logger'
    _rec_name = 'logger_name'

    logger_name = fields.Char('Name', required=True)
    work_manager_id = fields.Many2one(
        'work.manager', 'Work Manager')


class WorkLoggerMixin(models.AbstractModel):
    _name = 'work.logger.mixin'
    _description = 'Work Logger Mixin'

    work_logger_id = fields.Many2one(
        'work.logger', 'Work Logger',
        ondelete='restrict',
        auto_join=True, copy=False)
    work_manager_id = fields.Many2one(
        'work.manager', 'Work Manager',
        related='work_logger_id.work_manager_id')

    def work_get_logger_values(self):
        return {
            'logger_name': self.name_get()[0][1],
        }

    @api.model_cr_context
    def _init_column(self, name):
        """ Create aliases for existing rows. """
        super(WorkLoggerMixin, self)._init_column(name)
        if name != 'work_logger_id':
            return

        WorkLogger = self.env['work.logger'].sudo()
        ChildModel = self.sudo().with_context({
            'active_test': False,       # retrieve all records
            'prefetch_fields': False,   # do not prefetch fields on records
        })

        for record in ChildModel.search([('work_logger_id', '=', False)]):
            work_logger = WorkLogger.create(record.work_get_logger_values())
            record.with_context({'mail_notrack': True}).work_logger_id = work_logger
            _logger.info('Work Logger created for %s %s (id %s)',
                         record._name, record.display_name, record.id)

    @api.model
    def create(self, values):
        record = super(WorkLoggerMixin, self).create(values)
        work_logger = self.env['work.logger'].create(record.work_get_logger_values())
        record.write({'work_logger_id': work_logger.id})
        return record


class WorkManager(models.Model):
    _name = 'work.manager'
    _description = 'Work Manager'
    _rec_name = 'manager_name'

    manager_name = fields.Char('Name', required=True)
    manager_type = fields.Selection([
        ('other', 'Generic')], 'Type',
        default='other', required=True)


class WorkManagerMixin(models.AbstractModel):
    _name = 'work.manager.mixin'
    _description = 'Work Manager Mixin'

    work_manager_id = fields.Many2one(
        'work.manager', 'Work Manager',
        ondelete='restrict',
        auto_join=True, copy=False)

    def work_get_manager_values(self):
        return {
            'manager_name': self.name_get()[0][1],
        }

    @api.model_cr_context
    def _init_column(self, name):
        """ Create aliases for existing rows. """
        super(WorkManagerMixin, self)._init_column(name)
        if name != 'work_manager_id':
            return

        WorkManager = self.env['work.manager'].sudo()
        ChildModel = self.sudo().with_context({
            'active_test': False,       # retrieve all records
            'prefetch_fields': False,   # do not prefetch fields on records
        })

        for record in ChildModel.search([('work_manager_id', '=', False)]):
            work_manager = WorkManager.create(record.work_get_manager_values())
            record.with_context({'mail_notrack': True}).work_manager_id = work_manager
            _logger.info('Work Manager created for %s %s (id %s)',
                         record._name, record.display_name, record.id)

    @api.model
    def create(self, values):
        record = super(WorkManagerMixin, self).create(values)
        work_manager = self.env['work.manager'].create(record.work_get_manager_values())
        record.write({'work_manager_id': work_manager.id})
        return record
