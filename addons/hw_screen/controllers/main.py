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
from datetime import datetime
import subprocess
import openerp.tools.config as config
import time

_logger = logging.getLogger(__name__)

browser_pid = None
self_ip = config['xmlrpc_interface'] or '127.0.0.1'
self_port = config['xmlrpc_port'] or 8069


def proc_status(pid):
    for line in open("/proc/%d/status" % pid).readlines():
        if line.startswith("State:"):
            return line.split(":", 1)[1].strip().split(' ')[0]
    return None


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def _launch_browser():
    global browser_pid
    browser_pid = subprocess.Popen(["chromium-browser", self_ip + ":" + str(self_port) + "/point_of_sale/display"]).pid
    win_id = subprocess.check_output(['wmctrl', '-l', '-p', '|', 'grep ' + str(browser_pid), '|', 'cut', '-d " "', "-f0"])
    _logger.info(str(win_id))


def _test_browser():
    global browser_pid
    if not browser_pid:
        _launch_browser()
    if not check_pid(browser_pid):
        _launch_browser()
    elif proc_status(browser_pid) == 'Z':
        os.kill(browser_pid, 9)
        _launch_browser()


_test_browser()


pos_client_data = None
last_poll = None


class HardwareScreen(openerp.addons.web.controllers.main.Home):

    # POS CASHIER'S ROUTES
    @http.route('/hw_proxy/customer_facing_display', type='json', auth='none', cors='*')
    def update_user_facing_display(self, html=None):
        _test_browser()
        global pos_client_data
        request_ip = http.request.httprequest.remote_addr
        if not pos_client_data or request_ip == pos_client_data.get('ip_from', ''):
            pos_client_data = {'rendered_html': html,
                               'ip_from': request_ip,
                               'isNew': True}

            return {'status': 'updated'}
        else:
            return {'status': 'failed',
                    'message': 'Somebody else is using the display'}

    @http.route('/point_of_sale/take_control', type='json', auth='none', cors='*')
    def take_control(self, session_id=None):
        # ALLOW A CASHIER TO TAKE CONTROL OVER THE POSBOX, IN CASE OF MULTIPLE CASHIER PER POSBOX
        global pos_client_data

        if pos_client_data and not pos_client_data.get('ip_from') == http.request.httprequest.remote_addr:
            pos_client_data = {'ip_from': http.request.httprequest.remote_addr,
                               'rendered_html': '',
                               'isNew': True}

        return {'status': 'success',
                'message': 'You now have access to the display'}

    # POSBOX ROUTES (SELF)
    @http.route('/point_of_sale/display', type='http', auth='none', website=True)
    def render_main_display(self):
        return self._get_html()

    @http.route('/point_of_sale/get_serialized_order', type='http', auth='none')
    def get_serialized_order(self):
        global pos_client_data
        global last_poll
        last_poll = datetime.now()

        # IMPLEMENTATION OF LONGPOLLING
        if pos_client_data:
            while True:
                if pos_client_data.get('isNew'):
                    _logger.info(str(pos_client_data.get('isNew')))
                    pos_client_data["isNew"] = False
                    return dumps(pos_client_data)
        else:
            client_data = {'rendered_html': ''}
            return dumps(client_data)

    def _get_html(self):
        cust_js = None
        jquery = None
        bootstrap = None

        with open(os.path.join(os.path.dirname(__file__), "../static/src/js/worker.js")) as js:
            cust_js = js.read()

        with open(os.path.join(os.path.dirname(__file__), "../static/src/lib/jquery-3.1.1.min.js")) as jq:
            jquery = jq.read()

        with open(os.path.join(os.path.dirname(__file__), "../static/src/lib/bootstrap.css")) as btst:
            bootstrap = btst.read()

        html = """
            <!DOCTYPE html>
            <html>
                <head>
                <script type="text/javascript">
                    """ + jquery + """
                </script>
                <script type="text/javascript">
                    """ + cust_js + """
                </script>
                <style>
                    """ + bootstrap + """
                </style>
                </head>
                <body>
                    <div class="wrap"></div>
                </body>
                </html>
            """

        return html

    @http.route('/point_of_sale/test_ownership', type='json', auth='none', cors='*')
    def test_ownership(self):
        global pos_client_data
        if pos_client_data and pos_client_data.get('ip_from'):
            if not pos_client_data.get('ip_from') == http.request.httprequest.remote_addr:
                return {'status': 'NOWNER'}
        return {'status': 'OWNER'}
