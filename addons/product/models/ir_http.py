# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import logging

from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()
        result.update(self.get_uom_data())
        return result

    def get_decimals(self, rounding):
        """ returns the number of decimals digits from a "rounding" value.
              rounding    return
        E.g.:    0.001 ->      3
                0.0008 ->      4
                    10 ->      0
        """
        if 0 < rounding < 1:
            return int(math.ceil(math.log10(1.0 / rounding)))
        else:
            return 0

    def get_uom_data(self):
        """ Fetches the database's configured UoMs and returns their characteristics
        """
        weight_uom_id = request.env['ir.config_parameter'].get_param('database_weight_uom_id', default=request.env.ref('product.product_uom_kgm').id)
        if not weight_uom_id:
            _logger.warning("No unit of measure found to display weights, please make sure to set one in the General Settings. Falling back to hard-coded Kilos.")
            weight_data = {'name': 'kg', 'factor': 1, 'digits': [69, 3]}
        else:
            data = request.env['product.uom'].browse(int(weight_uom_id)).read(['name', 'factor', 'rounding'])[0]
            weight_data = {'name': data['name'], 'factor': data['factor'], 'digits': [69, self.get_decimals(data['rounding'])]}

        volume_uom_id = request.env['ir.config_parameter'].get_param('database_volume_uom_id', default=request.env.ref('product.product_uom_litre').id)
        if not volume_uom_id:
            _logger.warning("No unit of measure found to display volumes, please make sure to set one in the General Settings. Falling back to hard-coded Liters.")
            volume_data = {'name': 'Liter(s)', 'factor': 1, 'digits': [69, 3]}
        else:
            data = request.env['product.uom'].browse(int(volume_uom_id)).read(['name', 'factor', 'rounding'])[0]
            volume_data = {'name': data['name'], 'factor': data['factor'], 'digits': [69, self.get_decimals(data['rounding'])]}

        return {
            'weight_uom': weight_data,
            'volume_uom': volume_data,
        }
