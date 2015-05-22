# -*- coding: utf-8 -*-

from openerp import models, api

class account_payment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def print_checks(self):
        us_check_layout = self[0].company_id.us_check_layout
        if us_check_layout != 'disabled':
            return self.env['report'].get_action(self, self[0].company_id.us_check_layout)
        super(account_payment, self).print_checks()
