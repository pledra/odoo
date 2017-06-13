# -*- coding: utf-8 -*-
#----------------------------------------------------------
# ir_http modular http routing
#----------------------------------------------------------
import base64
import datetime
import hashlib
import logging
import mimetypes
import os
import re
import sys
import unicodedata

import werkzeug
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils

# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

import odoo
from odoo import api, http, models, tools, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request, STATIC_CACHE, content_disposition
from odoo.tools import config, pycompat, ustr
from odoo.tools.mimetypes import guess_mimetype
from odoo.modules.module import get_resource_path, get_module_path

_logger = logging.getLogger(__name__)


# global resolver (GeoIP API is thread-safe, for multithreaded workers)
# This avoids blowing up open files limit
odoo._geoip_resolver = None


# ------------------------------------------------------------
# Slug API
# ------------------------------------------------------------

def slugify(s, max_length=None):
    """ Transform a string to a slug that can be used in a url path.
        This method will first try to do the job with python-slugify if present.
        Otherwise it will process string by stripping leading and ending spaces,
        converting unicode chars to ascii, lowering all chars and replacing spaces
        and underscore with hyphen "-".
        :param s: str
        :param max_length: int
        :rtype: str
    """
    s = ustr(s)
    if slugify_lib:
        # There are 2 different libraries only python-slugify is supported
        try:
            return slugify_lib.slugify(s, max_length=max_length)
        except TypeError:
            pass
    uni = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    slug_str = re.sub('[\W_]', ' ', uni).strip().lower()
    slug_str = re.sub('[-\s]+', '-', slug_str)

    return slug_str[:max_length]


def slug(value):
    if isinstance(value, models.BaseModel):
        if isinstance(value.id, models.NewId):
            raise ValueError("Cannot slug non-existent record %s" % value)
        # [(id, name)] = value.name_get()
        identifier, name = value.id, value.display_name
    else:
        # assume name_search result tuple
        identifier, name = value
    slugname = slugify(name or '').strip().strip('-')
    if not slugname:
        return str(identifier)
    return "%s-%d" % (slugname, identifier)

# NOTE: as the pattern is used as it for the ModelConverter (ir_http.py), do not use any flags
_UNSLUG_RE = re.compile(r'(?:(\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(-?\d+)(?=$|/)')


def unslug(s):
    """Extract slug and id from a string.
        Always return un 2-tuple (str|None, int|None)
    """
    m = _UNSLUG_RE.match(s)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def unslug_url(s):
    """ From /blog/my-super-blog-1" to "blog/1" """
    parts = s.split('/')
    if parts:
        unslug_val = unslug(parts[-1])
        if unslug_val[1]:
            parts[-1] = str(unslug_val[1])
            return '/'.join(parts)
    return s


# ------------------------------------------------------------
# Language tools
# ------------------------------------------------------------

def url_for(path_or_uri, lang=None):
    if isinstance(path_or_uri, unicode):
        path_or_uri = path_or_uri.encode('utf-8')
    current_path = request.httprequest.path
    if isinstance(current_path, unicode):
        current_path = current_path.encode('utf-8')
    location = path_or_uri.strip()
    force_lang = lang is not None
    url = werkzeug.urls.url_parse(location)

    if request and not url.netloc and not url.scheme and (url.path or force_lang):
        location = werkzeug.urls.url_join(current_path, location)

        lang = lang or request.context.get('lang')
        langs = [lg[0] for lg in request.env['ir.http']._get_language_codes()]

        if (len(langs) > 1 or force_lang) and is_multilang_url(location, langs):
            ps = location.split('/')
            if ps[1] in langs:
                # Replace the language only if we explicitly provide a language to url_for
                if force_lang:
                    ps[1] = lang.encode('utf-8')
                # Remove the default language unless it's explicitly provided
                elif ps[1] == request.env['ir.http']._get_default_lang().code:
                    ps.pop(1)
            # Insert the context language or the provided language
            elif lang != request.env['ir.http']._get_default_lang().code or force_lang:
                ps.insert(1, lang.encode('utf-8'))
            location = '/'.join(ps)

    return location.decode('utf-8')


def is_multilang_url(local_url, langs=None):
    if not langs:
        langs = [lg[0] for lg in request.env['ir.http']._get_language_codes()]
    spath = local_url.split('/')
    # if a language is already in the path, remove it
    if spath[1] in langs:
        spath.pop(1)
        local_url = '/'.join(spath)
    try:
        # Try to match an endpoint in werkzeug's routing table
        url = local_url.split('?')
        path = url[0]
        query_string = url[1] if len(url) > 1 else None
        router = request.httprequest.app.get_db_router(request.db).bind('')
        # Force to check method to POST. Odoo uses methods : ['POST'] and ['GET', 'POST']
        func = router.match(path, method='POST', query_args=query_string)[0]
        return (func.routing.get('website', False) and
                func.routing.get('multilang', func.routing['type'] == 'http'))
    except Exception:
        return False


class RequestUID(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class ModelConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False, domain='[]'):
        super(ModelConverter, self).__init__(url_map)
        self.model = model
        self.domain = domain
        self.regex = _UNSLUG_RE.pattern

    def to_python(self, value):
        matching = re.match(self.regex, value)
        _uid = RequestUID(value=value, match=matching, converter=self)
        record_id = int(matching.group(2))
        env = api.Environment(request.cr, _uid, request.context)
        if record_id < 0:
            # limited support for negative IDs due to our slug pattern, assume abs() if not found
            if not env[self.model].browse(record_id).exists():
                record_id = abs(record_id)
        return env[self.model].browse(record_id)

    def to_url(self, value):
        return slug(value)


class ModelsConverter(werkzeug.routing.BaseConverter):

    def __init__(self, url_map, model=False):
        super(ModelsConverter, self).__init__(url_map)
        self.model = model
        # TODO add support for slug in the form [A-Za-z0-9-] bla-bla-89 -> id 89
        self.regex = r'([0-9,]+)'

    def to_python(self, value):
        _uid = RequestUID(value=value, converter=self)
        env = api.Environment(request.cr, _uid, request.context)
        return env[self.model].browse(int(v) for v in value.split(','))

    def to_url(self, value):
        return ",".join(value.ids)


class SignedIntConverter(werkzeug.routing.NumberConverter):
    regex = r'-?\d+'
    num_convert = int


class IrHttp(models.AbstractModel):
    _name = 'ir.http'
    _description = "HTTP routing"

    rerouting_limit = 10

    @classmethod
    def _get_converters(cls):
        return {'model': ModelConverter, 'models': ModelsConverter, 'int': SignedIntConverter}

    @classmethod
    def _find_handler(cls, return_rule=False):
        return cls.routing_map().bind_to_environ(request.httprequest.environ).match(return_rule=return_rule)

    @classmethod
    def _auth_method_user(cls):
        request.uid = request.session.uid
        if not request.uid:
            raise http.SessionExpiredException("Session expired")

    @classmethod
    def _auth_method_none(cls):
        request.uid = None

    @classmethod
    def _auth_method_public(cls):
        if not request.session.uid:
            request.uid = request.env.ref('base.public_user').id
        else:
            request.uid = request.session.uid

    @classmethod
    def _authenticate(cls, auth_method='user'):
        try:
            if request.session.uid:
                try:
                    request.session.check_security()
                    # what if error in security.check()
                    #   -> res_users.check()
                    #   -> res_users.check_credentials()
                except (AccessDenied, http.SessionExpiredException):
                    # All other exceptions mean undetermined status (e.g. connection pool full),
                    # let them bubble up
                    request.session.logout(keep_db=True)
            if request.uid is None:
                getattr(cls, "_auth_method_%s" % auth_method)()
        except (AccessDenied, http.SessionExpiredException, werkzeug.exceptions.HTTPException):
            raise
        except Exception:
            _logger.info("Exception during request Authentication.", exc_info=True)
            raise AccessDenied()
        return auth_method

    @classmethod
    def _serve_attachment(cls):
        env = api.Environment(request.cr, SUPERUSER_ID, request.context)
        domain = [('type', '=', 'binary'), ('url', '=', request.httprequest.path)]
        fields = ['__last_update', 'datas', 'name', 'mimetype', 'checksum']
        attach = env['ir.attachment'].search_read(domain, fields)
        if attach:
            wdate = attach[0]['__last_update']
            datas = attach[0]['datas'] or ''
            name = attach[0]['name']
            checksum = attach[0]['checksum'] or hashlib.sha1(datas).hexdigest()

            if (not datas and name != request.httprequest.path and
                    name.startswith(('http://', 'https://', '/'))):
                return werkzeug.utils.redirect(name, 301)

            response = werkzeug.wrappers.Response()
            server_format = tools.DEFAULT_SERVER_DATETIME_FORMAT
            try:
                response.last_modified = datetime.datetime.strptime(wdate, server_format + '.%f')
            except ValueError:
                # just in case we have a timestamp without microseconds
                response.last_modified = datetime.datetime.strptime(wdate, server_format)

            response.set_etag(checksum)
            response.make_conditional(request.httprequest)

            if response.status_code == 304:
                return response

            response.mimetype = attach[0]['mimetype'] or 'application/octet-stream'
            response.data = datas.decode('base64')
            return response

    @classmethod
    def _handle_exception(cls, exception):
        # If handle_exception returns something different than None, it will be used as a response

        # This is done first as the attachment path may
        # not match any HTTP controller
        if isinstance(exception, werkzeug.exceptions.HTTPException) and exception.code == 404:
            attach = cls._serve_attachment()
            if attach:
                return attach

        # Don't handle exception but use werkeug debugger if server in --dev mode
        if 'werkzeug' in tools.config['dev_mode']:
            raise
        try:
            return request._handle_exception(exception)
        except AccessDenied:
            return werkzeug.exceptions.Forbidden()

    bots = "bot|crawl|slurp|spider|curl|wget|facebookexternalhit".split("|")

    @classmethod
    def is_a_bot(cls):
        # We don't use regexp and ustr voluntarily
        # timeit has been done to check the optimum method
        user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '').lower()
        try:
            return any(bot in user_agent for bot in cls.bots)
        except UnicodeDecodeError:
            return any(bot in user_agent.encode('ascii', 'ignore') for bot in cls.bots)

    @classmethod
    def get_nearest_lang(cls, lang):
        # Try to find a similar lang. Eg: fr_BE and fr_FR
        short = lang.partition('_')[0]
        short_match = False
        for code, dummy in cls._get_language_codes():
            if code == lang:
                return lang
            if not short_match and code.startswith(short):
                short_match = code
        return short_match

    @classmethod
    def _geoip_setup_resolver(cls):
        # Lazy init of GeoIP resolver
        if odoo._geoip_resolver is not None:
            return
        try:
            import GeoIP
            # updated database can be downloaded on MaxMind website
            # http://dev.maxmind.com/geoip/legacy/install/city/
            geofile = config.get('geoip_database')
            if os.path.exists(geofile):
                odoo._geoip_resolver = GeoIP.open(geofile, GeoIP.GEOIP_STANDARD)
            else:
                odoo._geoip_resolver = False
                _logger.warning('GeoIP database file %r does not exists, apt-get install geoip-database-contrib or download it from http://dev.maxmind.com/geoip/legacy/install/city/', geofile)
        except ImportError:
            odoo._geoip_resolver = False

    @classmethod
    def _geoip_resolve(cls):
        if 'geoip' not in request.session:
            record = {}
            if odoo._geoip_resolver and request.httprequest.remote_addr:
                record = odoo._geoip_resolver.record_by_addr(request.httprequest.remote_addr) or {}
            request.session['geoip'] = record

    @classmethod
    def _add_dispatch_parameters(cls, func, first_pass):
        if request.website_enabled:
            request.redirect = lambda url, code=302: werkzeug.utils.redirect(url_for(url), code)
            context = dict(request.context)

            if not context.get('tz'):
                context['tz'] = request.session.get('geoip', {}).get('time_zone')

            path = request.httprequest.path.split('/')
            if first_pass:
                langs = [lg.code for lg in cls._get_languages()]
                is_a_bot = cls.is_a_bot()
                cook_lang = request.httprequest.cookies.get('website_lang')
                nearest_lang = not func and cls.get_nearest_lang(path[1])
                preferred_lang = ((cook_lang if cook_lang in langs else False)
                                  or (not is_a_bot and cls.get_nearest_lang(request.lang))
                                  or cls._get_default_lang().code)

                request.lang = context['lang'] = nearest_lang or preferred_lang

            if path[1] == cls._get_default_lang().code:
                context['edit_translations'] = False

            # bind modified context
            request.context = context

    @classmethod
    def _dispatch(cls):
        """ Before executing the endpoint method, add website params on request, such as
                - current website (record)
                - multilang support (set on cookies)
                - geoip dict data are added in the session
            Then follow the parent dispatching.
            Reminder :  Do not use `request.env` before authentication phase, otherwise the env
                        set on request will be created with uid=None (and it is a lazy property)
        """
        first_pass = not hasattr(request, 'website_enabled')

        func = None
        # locate the controller method
        try:
            if request.httprequest.method == 'GET' and '//' in request.httprequest.path:
                new_url = request.httprequest.path.replace('//', '/') + '?' + request.httprequest.query_string
                return werkzeug.utils.redirect(new_url, 301)
            rule, arguments = cls._find_handler(return_rule=True)
            func = rule.endpoint
            request.website_enabled = func.routing.get('website', False)
        except werkzeug.exceptions.NotFound as e:
            # either we have a language prefixed route, either a real 404
            # in all cases, website processes them
            request.website_enabled = True
            # return cls._handle_exception(e)

        request.website_multilang = (
            request.website_enabled and
            func and func.routing.get('multilang', func.routing['type'] == 'http')
        )

        cls._geoip_setup_resolver()
        cls._geoip_resolve()

        # check authentication level
        try:
            if func:
                cls._authenticate(func.routing['auth'])
            elif request.uid is None and request.website_enabled:
                cls._auth_method_public()
        except Exception as e:
            return cls._handle_exception(e)

        # For website routes (only), add website params on `request`
        cook_lang = request.httprequest.cookies.get('website_lang')
        if request.website_enabled:
            request.redirect = lambda url, code=302: werkzeug.utils.redirect(url_for(url), code)

            cls._add_dispatch_parameters(func, first_pass)

            path = request.httprequest.path.split('/')
            if first_pass:
                is_a_bot = cls.is_a_bot()
                nearest_lang = not func and cls.get_nearest_lang(path[1])
                url_lang = nearest_lang and path[1]

                # if lang in url but not the displayed or default language --> change or remove
                # or no lang in url, and lang to dispay not the default language --> add lang
                # and not a POST request
                # and not a bot or bot but default lang in url
                if ((url_lang and (url_lang != request.lang or url_lang == cls._get_default_lang().code))
                        or (not url_lang and request.website_multilang and request.lang != cls._get_default_lang().code)
                        and request.httprequest.method != 'POST') \
                        and (not is_a_bot or (url_lang and url_lang == cls._get_default_lang().code)):
                    if url_lang:
                        path.pop(1)
                    if request.lang != cls._get_default_lang().code:
                        path.insert(1, request.lang)
                    path = '/'.join(path) or '/'
                    # request.context = context
                    redirect = request.redirect(path + '?' + request.httprequest.query_string)
                    redirect.set_cookie('website_lang', request.lang)
                    return redirect
                elif url_lang:
                    request.uid = None
                    path.pop(1)
                    # request.context = context
                    return cls.reroute('/'.join(path) or '/')

        # removed cache for auth public
        request.cache_save = False

        # locate the controller method
        try:
            rule, arguments = cls._find_handler(return_rule=True)
            func = rule.endpoint
        except werkzeug.exceptions.NotFound as e:
            return cls._handle_exception(e)

        processing = cls._postprocess_args(arguments, rule)
        if processing:
            return processing

        # set and execute handler
        try:
            request.set_handler(func, arguments, func.routing["auth"])
            result = request.dispatch()
            if isinstance(result, Exception):
                raise result
        except Exception as e:
            return cls._handle_exception(e)

        if request.website_enabled and cook_lang != request.lang and hasattr(result, 'set_cookie'):
            result.set_cookie('website_lang', request.lang)

        return result

    @classmethod
    def _get_languages(cls):
        return request.env['res.lang'].search([])

    @classmethod
    def _get_language_codes(cls):
        languages = cls._get_languages()
        return [(lang.code, lang.name) for lang in languages]

    @classmethod
    def _get_default_lang(cls):
        lang_code = request.env['ir.values'].sudo().get_default('res.partner', 'lang')
        if lang_code:
            return request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return request.env['res.lang'].search([], limit=1)

    @classmethod
    def _postprocess_args(cls, arguments, rule):
        """ post process arg to set uid on browse records """
        for key, val in list(pycompat.items(arguments)):
            # Replace uid placeholder by the current request.uid
            if isinstance(val, models.BaseModel) and isinstance(val._uid, RequestUID):
                arguments[key] = val.sudo(request.uid)
                if not val.exists():
                    return cls._handle_exception(werkzeug.exceptions.NotFound())

        try:
            _, path = rule.build(arguments)
            assert path is not None
        except Exception as e:
            return cls._handle_exception(e, code=404)

        if getattr(request, 'website_multilang', False) and request.httprequest.method in ('GET', 'HEAD'):
            generated_path = werkzeug.url_unquote_plus(path)
            current_path = werkzeug.url_unquote_plus(request.httprequest.path)
            if generated_path != current_path:
                if request.lang != cls._get_default_lang().code:
                    path = '/' + request.lang + path
                if request.httprequest.query_string:
                    path += '?' + request.httprequest.query_string
                return werkzeug.utils.redirect(path, code=301)

    @classmethod
    def reroute(cls, path):
        if not hasattr(request, 'rerouting'):
            request.rerouting = [request.httprequest.path]
        if path in request.rerouting:
            raise Exception("Rerouting loop is forbidden")
        request.rerouting.append(path)
        if len(request.rerouting) > cls.rerouting_limit:
            raise Exception("Rerouting limit exceeded")
        request.httprequest.environ['PATH_INFO'] = path
        # void werkzeug cached_property. TODO: find a proper way to do this
        for key in ('path', 'full_path', 'url', 'base_url'):
            request.httprequest.__dict__.pop(key, None)

        return cls._dispatch()

    @classmethod
    def routing_map(cls):
        if not hasattr(cls, '_routing_map'):
            _logger.info("Generating routing map")
            installed = request.registry._init_modules - {'web'}
            if tools.config['test_enable']:
                installed.add(odoo.modules.module.current_test)
            mods = [''] + odoo.conf.server_wide_modules + sorted(installed)
            # Note : when routing map is generated, we put it on the class `cls`
            # to make it available for all instance. Since `env` create an new instance
            # of the model, each instance will regenared its own routing map and thus
            # regenerate its EndPoint. The routing map should be static.
            cls._routing_map = http.routing_map(mods, False, converters=cls._get_converters())
        return cls._routing_map

    @classmethod
    def _clear_routing_map(cls):
        if hasattr(cls, '_routing_map'):
            del cls._routing_map

    @classmethod
    def content_disposition(cls, filename):
        return content_disposition(filename)

    @classmethod
    def binary_content(cls, xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
        """ Get file, attachment or downloadable content

        If the ``xmlid`` and ``id`` parameter is omitted, fetches the default value for the
        binary field (via ``default_get``), otherwise fetches the field for
        that precise record.

        :param str xmlid: xmlid of the record
        :param str model: name of the model to fetch the binary from
        :param int id: id of the record from which to fetch the binary
        :param str field: binary field
        :param bool unique: add a max-age for the cache control
        :param str filename: choose a filename
        :param str filename_field: if not create an filename with model-id-field
        :param bool download: apply headers to download the file
        :param str mimetype: mintype of the field (for headers)
        :param str default_mimetype: default mintype if no mintype found
        :param Environment env: by default use request.env
        :returns: (status, headers, content)
        """
        env = env or request.env
        # get object and content
        obj = None
        if xmlid:
            obj = env.ref(xmlid, False)
        elif id and model in env.registry:
            obj = env[model].browse(int(id))

        # obj exists
        if not obj or not obj.exists() or field not in obj:
            return (404, [], None)

        # check read access
        try:
            last_update = obj['__last_update']
        except AccessError:
            return (403, [], None)

        status, headers, content = None, [], None

        # attachment by url check
        module_resource_path = None
        if model == 'ir.attachment' and obj.type == 'url' and obj.url:
            url_match = re.match("^/(\w+)/(.+)$", obj.url)
            if url_match:
                module = url_match.group(1)
                module_path = get_module_path(module)
                module_resource_path = get_resource_path(module, url_match.group(2))
                if module_path and module_resource_path:
                    module_path = os.path.join(os.path.normpath(module_path), '')  # join ensures the path ends with '/'
                    module_resource_path = os.path.normpath(module_resource_path)
                    if module_resource_path.startswith(module_path):
                        with open(module_resource_path, 'rb') as f:
                            content = base64.b64encode(f.read())
                        last_update = str(os.path.getmtime(module_resource_path))

            if not module_resource_path:
                module_resource_path = obj.url

            if not content:
                status = 301
                content = module_resource_path
        else:
            content = obj[field] or ''

        # filename
        if not filename:
            if filename_field in obj:
                filename = obj[filename_field]
            elif module_resource_path:
                filename = os.path.basename(module_resource_path)
            else:
                filename = "%s-%s-%s" % (obj._name, obj.id, field)

        # mimetype
        mimetype = 'mimetype' in obj and obj.mimetype or False
        if not mimetype:
            if filename:
                mimetype = mimetypes.guess_type(filename)[0]
            if not mimetype and getattr(env[model]._fields[field], 'attachment', False):
                # for binary fields, fetch the ir_attachement for mimetype check
                attach_mimetype = env['ir.attachment'].search_read(domain=[('res_model', '=', model), ('res_id', '=', id), ('res_field', '=', field)], fields=['mimetype'], limit=1)
                mimetype = attach_mimetype and attach_mimetype[0]['mimetype']
            if not mimetype:
                mimetype = guess_mimetype(base64.b64decode(content), default=default_mimetype)

        headers += [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff')]

        # cache
        etag = hasattr(request, 'httprequest') and request.httprequest.headers.get('If-None-Match')
        retag = '"%s"' % hashlib.md5(last_update).hexdigest()
        status = status or (304 if etag == retag else 200)
        headers.append(('ETag', retag))
        headers.append(('Cache-Control', 'max-age=%s' % (STATIC_CACHE if unique else 0)))

        # content-disposition default name
        if download:
            headers.append(('Content-Disposition', cls.content_disposition(filename)))
        return (status, headers, content)


def convert_exception_to(to_type, with_message=False):
    """ Should only be called from an exception handler. Fetches the current
    exception data from sys.exc_info() and creates a new exception of type
    ``to_type`` with the original traceback.

    If ``with_message`` is ``True``, sets the new exception's message to be
    the stringification of the original exception. If ``False``, does not
    set the new exception's message. Otherwise, uses ``with_message`` as the
    new exception's message.

    :type with_message: str|bool
    """
    etype, original, tb = sys.exc_info()
    try:
        if with_message is False:
            message = None
        elif with_message is True:
            message = str(original)
        else:
            message = str(with_message)

        raise pycompat.reraise(to_type, to_type(message), tb)
    except to_type as e:
        return e
