# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2015 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import logging

from openerp import http
import openerp
import os
from json import dumps

_logger = logging.getLogger(__name__)


# def _launch_browser():
#     # TODO
#     json.load()


browser_pid = None
# if not browser_pid:
#    _launch_browser()
# invoke shell command to launch the browser full screen

# Maintains data about the client (Cashier)
# Form:
# {ip_from,
# datetime,
# sale_order}
pos_client_data = None


class HardwareScreen(openerp.addons.web.controllers.main.Home):

    # POS CASHIER'S ROUTES
    @http.route('/hw_proxy/customer_facing_display', type='json', auth='none', cors='*')
    def update_user_facing_display(self, pos_data_html):
        # process pos_data from the cashier's JS to make it a file
        # file contains metadata and html
        request_ip = None
        if not pos_client_data | request_ip == pos_client_data.ip_from:
            global pos_client_data
            pos_client_data = pos_data_html
            return {'status': 'updated'}
        else:
            return {'status': 'failed',
                    'message': 'Somebody else is using the display'}

    @http.route('/point_of_sale/take_control')
    def take_control(self):
        # ALLOW A CASHIER TO TAKE CONTROL OVER THE POSBOX, IN CASE OF MULTIPLE CASHIER PER POSBOX
        global pos_client_data
        pos_client_data = None
        return {'status': 'success',
                'message': 'You now have access to the display'}

    # POSBOX ROUTES (SELF)
    @http.route('/point_of_sale/display', type='http', auth='none', website=True)
    def render_main_display(self):
        html = None
        with open(os.path.join(os.path.dirname(__file__), "template.html")) as template:
            html = template.read()
        return html

    @http.route('/point_of_sale/get_serialized_order', type='http', auth='none')
    def get_serialized_order(self):
        # CHECK IP AND SESSION AND CONTROL
        # RETURN THE ENTIRE ORDER
        global pos_client_data
        pos_client_data = {'cust_logo': 'cust_logo',
                           'cust_message': 'cust_mess',
                           'orders': [{'order_id': '1', 'product': 'tamere'}, {'order_id': '2', 'product':'tasoeur'}]
                           }

        return dumps(pos_client_data)
