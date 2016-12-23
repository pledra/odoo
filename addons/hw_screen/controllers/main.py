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
import openerp.tools.config as config
import threading
import netifaces as ni
from subprocess import call

_logger = logging.getLogger(__name__)

browser_pid = None
self_ip = config['xmlrpc_interface'] or '127.0.0.1'
self_port = config['xmlrpc_port'] or 8069

event_data = threading.Event()
pos_client_data = {'rendered_html': '',
                   'ip_from': ''}


class HardwareScreen(openerp.addons.web.controllers.main.Home):

    def screen_wake_up(self):
        os.environ['DISPLAY'] = ":0"
        os.environ['XAUTHORITY'] = "/tmp/.Xauthority"
        call(['sudo', 'xdotool', 'key', 'ctrl'])

    @http.route('/hw_proxy/display_refresh', type='json', auth='none', cors='*')
    def display_refresh(self):
        os.environ['DISPLAY'] = ":0"
        os.environ['XAUTHORITY'] = "/tmp/.Xauthority"
        call(['sudo', 'xdotool', 'key', 'F5'])
        return "Display Refreshed"


    # POS CASHIER'S ROUTES
    @http.route('/hw_proxy/customer_facing_display', type='json', auth='none', cors='*')
    def update_user_facing_display(self, html=None):
        global pos_client_data
        request_ip = http.request.httprequest.remote_addr
        if request_ip == pos_client_data.get('ip_from', ''):
            pos_client_data['rendered_html'] = html
            global event_data
            self.screen_wake_up()
            event_data.set()

            return {'status': 'updated'}
        else:
            return {'status': 'failed',
                    'message': 'Somebody else is using the display'}

    @http.route('/hw_proxy/take_control', type='json', auth='none', cors='*')
    def take_control(self, html=None):
        # ALLOW A CASHIER TO TAKE CONTROL OVER THE POSBOX, IN CASE OF MULTIPLE CASHIER PER POSBOX
        global pos_client_data
        global event_data
        pos_client_data['rendered_html'] = html
        pos_client_data['ip_from'] = http.request.httprequest.remote_addr
        event_data.set()

        return {'status': 'success',
                'message': 'You now have access to the display'}

    @http.route('/hw_proxy/test_ownership', type='json', auth='none', cors='*')
    def test_ownership(self):
        global pos_client_data
        if pos_client_data.get('ip_from') == http.request.httprequest.remote_addr:
            return {'status': 'OWNER'}
        else:
            return {'status': 'NOWNER'}

    # POSBOX ROUTES (SELF)
    @http.route('/point_of_sale/display', type='http', auth='none', website=True)
    def render_main_display(self):
        return self._get_html()

    @http.route('/point_of_sale/get_serialized_order', type='json', auth='none')
    def get_serialized_order(self):
        global event_data
        global pos_client_data
        result = pos_client_data
        # IMPLEMENTATION OF LONGPOLLING
        if event_data.wait():
            event_data.clear()
            return result
        else:
            event_data.clear()
            return result

    def _get_html(self):
        cust_js = None
        jquery = None
        bootstrap = None
        interfaces = ni.interfaces()

        with open(os.path.join(os.path.dirname(__file__), "../static/src/js/worker.js")) as js:
            cust_js = js.read()

        with open(os.path.join(os.path.dirname(__file__), "../static/src/lib/jquery-3.1.1.min.js")) as jq:
            jquery = jq.read()

        with open(os.path.join(os.path.dirname(__file__), "../static/src/lib/bootstrap.css")) as btst:
            bootstrap = btst.read()

        with open(os.path.join(os.path.dirname(__file__), "../static/src/css/cust_css.css")) as css:
            cust_css = css.read()

        display_ifaces = ""
        for iface_id in interfaces:
            iface_obj = ni.ifaddresses(iface_id)
            ifconfigs = iface_obj.get(ni.AF_INET, [])
            for conf in ifconfigs:
                if conf.get('addr'):
                    display_ifaces += "<tr><td>" + iface_id + "</td>"
                    display_ifaces += "<td>" + conf.get('addr') + "</td>"
                    display_ifaces += "<td>" + conf.get('netmask') + "</td></tr>"

        html = """
            <!DOCTYPE html>
            <html>
                <head>
                <title>Odoo -- Point of Sale</title>
                <script type="text/javascript">
                    """ + jquery + """
                </script>
                <script type="text/javascript">
                    """ + cust_js + """
                </script>
                <style>
                    """ + bootstrap + """
                </style>
                <style>
                    """ + cust_css + """
                </style>
                </head>
                <body>
                    <div hidden class="shadow"></div>
                    <div class="container">
                    <div class="row">
                        <div class="col-md-4 col-md-offset-4">
                            <h1>Odoo Point of Sale</h1>
                            <h2>POSBox Client display</h2>
                            <h3>My IPs</h3>
                                <table id="table_ip" class="table table-condensed">
                                    <tr>
                                        <th>Interface</th>
                                        <th>IP</th>
                                        <th>Netmask</th>
                                    </tr>
                                    """ + display_ifaces + """
                                </table>
                        </div>
                    </div>
                    </div>
                </body>
                </html>
            """
        return html

