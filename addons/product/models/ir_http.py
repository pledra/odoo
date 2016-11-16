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
        result.update({"weight_uom": self.get_weight_uom()})
        return result

    def get_weight_uom(self):
        """ Fetches the configured UoM for weights and returns its characteristics
        """
        def get_decimals(rounding):
            """ returns the number of decimals digits from a "rounding".
            E.g.: 0.001 -> 3
                  0.0008 -> 4
            """
            if 0 < rounding < 1:
                return int(math.ceil(math.log10(1.0 / rounding)))
            else:
                return 0

        weight_uom_id = request.env['ir.config_parameter'].get_param('database_weight_uom_id', default=request.env.ref('product.product_uom_kgm').id)
        if weight_uom_id:
            weight_uom = request.env['product.uom'].browse(int(weight_uom_id))
            data = weight_uom.read(['name', 'factor', 'rounding'])[0]
            return {'name': data['name'], 'factor': data['factor'], 'digits': [69, get_decimals(data['rounding'])]}
        else:
            _logger.warning("No unit of measure found to display weights, please make sure to set one in the General Settings. Falling back to hard-coded Kilos.")
            return {'name': 'kg', 'factor': 1, 'digits': [69, 3]}
