from odoo import http
from odoo.addons.web.controllers.main import set_cookie_and_redirect, login_and_redirect
from odoo import registry as registry_get

import logging
import werkzeug

_logger = logging.getLogger(__name__)


class AuthTokenController(http.Controller):

    @http.route('/auth_token/login', type='http', methods=['GET'], auth='none')
    def impersonate(self, login, db, token, redirect='', **kw):
        registry = registry_get(db)
        with registry.cursor():
            redirect = werkzeug.url_unquote_plus(redirect)
            url = '/web' or redirect
            remote = http.request.httprequest.remote_addr
            _logger.info('auth_token: authentication attempt as %s on database %s from remote address %s' % (login, db, remote))
            return login_and_redirect(db, login, token, redirect_url=url)
        return set_cookie_and_redirect(url)
