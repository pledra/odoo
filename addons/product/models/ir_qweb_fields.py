# -*- coding: utf-8 -*-
import math

from odoo import api, models, _

import logging
_logger = logging.getLogger(__name__)


class WeightConverter(models.AbstractModel):
    """ ``weight`` converter, transforms a float field stored in the DB's
    default weight UoM (kg) to the chosen UoM.
    By default, the chosen UoM is the one set in the General Settings unless
    one is specified in the options under "weight_uom".

    E.g.: <span t-field="record.weight"
                t-options="{'widget': 'weight', 'weight_uom': record.weight_uom_id}"/>

    The weight value will be converted using the UoM factor and rounding and
    the html value will also display the UoM's name.
    """
    _name = 'ir.qweb.field.weight'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        formatted_amount = "%.{0}f".format(options['rounding']) % value
        return u'<span class="oe_weight_value">{0}\N{NO-BREAK SPACE}</span>{uom}'.format(formatted_amount, uom=options['name'])

    @api.model
    def record_to_html(self, record, field_name, options):
        options = dict(options)

        weight_data = []
        if options.get('weight_uom'):
            if not options.get('weight_uom').category_id or options.get('weight_uom').category_id.id != self.env.ref('product.product_uom_categ_kgm').id:
                _logger.error(_('Attempted to use Qweb weight widget with wrong UoM category. Falling back to defaults.'))
            else:
                weight_data = options.get('weight_uom').read(['name', 'factor', 'rounding'])[0]

        if not weight_data:
            weight_uom_id = self.env['ir.config_parameter'].get_param('database_weight_uom_id', default=self.env.ref('product.product_uom_kgm').id)
            if weight_uom_id:
                weight_data = self.env['product.uom'].browse(int(weight_uom_id)).read(['name', 'factor', 'rounding'])[0]
            else:
                _logger.warning("No unit of measure found to display weights, please make sure to set one in the General Settings. Falling back to hard-coded Kilos.")
                weight_data = {'name': 'kg', 'factor': 1, 'digits': [69, 3]}

        if 0 < weight_data['rounding'] < 1:
            rounding = int(math.ceil(math.log10(1.0 / weight_data['rounding'])))
        else:
            rounding = 0

        options.update({'name': weight_data['name'], 'rounding': rounding})
        value = record[field_name] * weight_data['factor']

        return self.value_to_html(value, options)


class VolumeConverter(models.AbstractModel):
    """ ``volume`` converter, transforms a float field stored in the DB's
    default volume UoM (kg) to the chosen UoM.
    By default, the chosen UoM is the one set in the General Settings unless
    one is specified in the options under "volume_uom".

    E.g.: <span t-field="record.volume"
                t-options="{'widget': 'volume', 'volume_uom': record.volume_uom_id}"/>

    The volume value will be converted using the UoM factor and rounding and
    the html value will also display the UoM's name.
    """
    _name = 'ir.qweb.field.volume'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        formatted_amount = "%.{0}f".format(options['rounding']) % value
        return u'<span class="oe_volume_value">{0}\N{NO-BREAK SPACE}</span>{uom}'.format(formatted_amount, uom=options['name'])

    @api.model
    def record_to_html(self, record, field_name, options):
        options = dict(options)

        volume_data = []
        if options.get('volume_uom'):
            if not options.get('volume_uom').category_id or options.get('volume_uom').category_id.id != self.env.ref('product.product_uom_categ_vol').id:
                _logger.error(_('Attempted to use Qweb volume widget with wrong UoM category. Falling back to defaults.'))
            else:
                volume_data = options.get('volume_uom').read(['name', 'factor', 'rounding'])[0]

        if not volume_data:
            volume_uom_id = self.env['ir.config_parameter'].get_param('database_volume_uom_id', default=self.env.ref('product.product_uom_litre').id)
            if volume_uom_id:
                volume_data = self.env['product.uom'].browse(int(volume_uom_id)).read(['name', 'factor', 'rounding'])[0]
            else:
                _logger.warning("No unit of measure found to display weights, please make sure to set one in the General Settings. Falling back to hard-coded Kilos.")
                volume_data = {'name': 'kg', 'factor': 1, 'digits': [69, 3]}

        if 0 < volume_data['rounding'] < 1:
            rounding = int(math.ceil(math.log10(1.0 / volume_data['rounding'])))
        else:
            rounding = 0

        options.update({'name': volume_data['name'], 'rounding': rounding})
        value = record[field_name] * volume_data['factor']

        return self.value_to_html(value, options)
