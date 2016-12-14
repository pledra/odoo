# -*- coding: utf-8 -*-

from odoo import api, fields, models


class event_config_settings(models.TransientModel):
    _name = 'event.config.settings'
    _inherit = 'res.config.settings'

    module_event_sale = fields.Boolean("Tickets", help='Install the event_sale module')
    module_website_event = fields.Boolean("Online Events", help="Install the module website_event")
    module_website_event_track = fields.Boolean("Tracks & Agenda", help='Install the module website_event_track')
    module_website_event_sale = fields.Boolean("Online Ticketing", help="Install the module website_event_sale")
    module_website_event_questions = fields.Boolean("Questions", help='Install the website_event_questions module')
    module_event_barcode = fields.Boolean("Barcode", help="Install the event_barcode module")
    manual_confirmation = fields.Boolean("Manual Confirmation", help='Select this option to manually manage draft event and draft registration')

    @api.multi
    def set_default_auto_confirmation(self):
        if self.env.user._is_admin() or self.env['res.users'].has_group('event.group_event_manager'):
            IrValues = self.env['ir.values'].sudo()
        else:
            IrValues = self.env['ir.values']
        IrValues.set_default('event.config.settings', 'manual_confirmation', self.manual_confirmation)
