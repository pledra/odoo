# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api


# This will create the tables for the financial report objects so they can be instanced in other modules
# like the l10n modules. For fully functional reports, account_reports is required.
class ReportAccountFinancialReport(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    name = fields.Char()
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    line_ids = fields.One2many('account.financial.report.line', 'financial_report_id', string='Lines')
    report_type = fields.Selection([('date_range', 'Based on date ranges'),
                                    ('date_range_extended', "Based on date ranges with 'older' and 'total' columns and last 3 months"),
                                    ('no_date_range', 'Based on a single date'),
                                    ('date_range_cash', 'Bases on date ranges and cash basis method')],
                                   string='Analysis Periods', default=False, required=True,
                                   help='For report like the balance sheet that do not work with date ranges')
    company_id = fields.Many2one('res.company', string='Company')
    menuitem_created = fields.Boolean(default=False)


class AccountFinancialReportLine(models.Model):
    _name = "account.financial.report.line"
    _description = "Account Report Line"
    _order = "sequence"

    name = fields.Char('Section Name')
    code = fields.Char('Code')
    financial_report_id = fields.Many2one('account.financial.report', 'Financial Report')
    parent_id = fields.Many2one('account.financial.report.line', string='Parent')
    children_ids = fields.One2many('account.financial.report.line', 'parent_id', string='Children')
    sequence = fields.Integer()

    domain = fields.Char(default=None)
    formulas = fields.Char()
    groupby = fields.Char(default=False)
    figure_type = fields.Selection([('float', 'Float'), ('percents', 'Percents'), ('no_unit', 'No Unit')],
                                   'Type', default='float', required=True)
    green_on_positive = fields.Boolean('Is growth good when positive', default=True)
    level = fields.Integer(required=True)
    special_date_changer = fields.Selection([('from_beginning', 'From the beginning'), ('to_beginning_of_period', 'At the beginning of the period'), ('normal', 'Use given dates')], default='normal')
    show_domain = fields.Selection([('always', 'Always'), ('never', 'Never'), ('foldable', 'Foldable')], default='foldable')
    hide_if_zero = fields.Boolean(default=False)
    action_id = fields.Many2one('ir.actions.actions')


class AccountFinancialReportXMLExport(models.AbstractModel):
    _name = "account.financial.report.xml.export"
    _description = "All the xml exports available for the financial reports"

    @api.model
    def is_xml_export_available(self, report_name, report_id=None):
        return False

    def check(self, report_name, report_id=None):
        return True

    def do_xml_export(self, report_id, context_id):
        return ''
