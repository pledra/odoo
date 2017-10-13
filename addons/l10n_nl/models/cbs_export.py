# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

import calendar
from datetime import datetime


class CbsExport(models.Model):
    _inherit = 'l10n_nl.cbs.export'

    @api.multi
    def _default_get_month(self):
        context_today = fields.Date.context_today(self)
        return fields.Date.from_string(context_today).strftime('%m')

    @api.model
    def _default_get_year(self):
        context_today = fields.Date.context_today(self)
        return fields.Date.from_string(context_today).strftime('%Y')

    name = fields.Char(string='Name', readonly=True)
    attachment_id = fields.Many2one('ir.attachment', string='File', readonly=True)
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], required=True, default=_default_get_month)
    year = fields.Char(size=4, required=True, default=_default_get_year)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id)
    invoice_ids = fields.One2many('account.invoice', 'cbs_export_id', string='Invoices', readonly=True)

    _sql_constraints = [(
        'month_year_company_unique', 'unique(month, year, company_id)',
        _('A CBS export already exists with the same month and year for this company.')
    )]

    @api.multi
    def fetch_invoice_ids(self):
        intrastat_countries = self.env.ref('base.europe').country_ids - self.env.ref('base.nl')
        month = int(self.month)
        year = int(self.year)
        days = calendar.monthrange(year, month)
        self.env['account.invoice'].search([
            ('type', '=', 'out_invoice'),
            ('state', 'in', ['open', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('partner_id.country_id.in', '=', intrastat_countries.ids),
            ('date_invoice', '>=', datetime.strptime('%s-%s-%s' % (1, month, year), '%d-%m-%Y')),
            ('date_invoice', '<=', datetime.strptime('%s-%s-%s' % (days[1], month, year), '%d-%m-%Y'))
        ]).write({'cbs_export_id': self.id})

    @api.model
    def create(self, vals):
        res = super(CbsExport, self).create(vals)
        res.name = self.env['ir.sequence'].next_by_code('cbs.export.file')
