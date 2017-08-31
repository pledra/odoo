# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
import hashlib
import re

from werkzeug import urls
from werkzeug.exceptions import NotFound

from odoo import api, fields, models, tools
from odoo.addons.http_routing.models.ir_http import slugify, unslug
from odoo.addons.portal.controllers.portal import pager
from odoo.tools import pycompat
from odoo.http import request
from odoo.tools.translate import _

logger = logging.getLogger(__name__)


DEFAULT_CDN_FILTERS = [
    "^/[^/]+/static/",
    "^/web/(css|js)/",
    "^/web/image",
    "^/web/content",
    # retrocompatibility
    "^/website/image/",
]


class Website(models.Model):

    _name = "website"  # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"

    def _active_languages(self):
        return self.env['res.lang'].search([]).ids

    def _default_language(self):
        lang_code = self.env['ir.default'].get('res.partner', 'lang')
        def_lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return def_lang.id if def_lang else self._active_languages()[0]

    name = fields.Char('Website Name')
    domain = fields.Char('Website Domain')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.ref('base.main_company').id)
    language_ids = fields.Many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages', default=_active_languages)
    default_lang_id = fields.Many2one('res.lang', string="Default Language", default=_default_language, required=True)
    default_lang_code = fields.Char(related='default_lang_id.code', string="Default language code", store=True)

    social_twitter = fields.Char(related="company_id.social_twitter")
    social_facebook = fields.Char(related="company_id.social_facebook")
    social_github = fields.Char(related="company_id.social_github")
    social_linkedin = fields.Char(related="company_id.social_linkedin")
    social_youtube = fields.Char(related="company_id.social_youtube")
    social_googleplus = fields.Char(related="company_id.social_googleplus")

    google_analytics_key = fields.Char('Google Analytics Key')
    google_management_client_id = fields.Char('Google Client ID')
    google_management_client_secret = fields.Char('Google Client Secret')

    user_id = fields.Many2one('res.users', string='Public User', default=lambda self: self.env.ref('base.public_user').id)
    cdn_activated = fields.Boolean('Activate CDN for assets')
    cdn_url = fields.Char('CDN Base URL', default='')
    cdn_filters = fields.Text('CDN Filters', default=lambda s: '\n'.join(DEFAULT_CDN_FILTERS), help="URL matching those filters will be rewritten using the CDN Base URL")
    partner_id = fields.Many2one(related='user_id.partner_id', relation='res.partner', string='Public Partner')
    menu_id = fields.Many2one('website.menu', compute='_compute_menu', string='Main Menu')
    homepage_id = fields.Many2one('website.page', string='Homepage')
    favicon = fields.Binary(string="Website Favicon", help="This field holds the image used to display a favicon on the website.")

    @api.multi
    def _compute_menu(self):
        Menu = self.env['website.menu']
        for website in self:
            website.menu_id = Menu.search([('parent_id', '=', False), ('website_id', '=', website.id)], order='id', limit=1).id

    # cf. Wizard hack in website_views.xml
    def noop(self, *args, **kwargs):
        pass

    @api.multi
    def write(self, values):
        self._get_languages.clear_cache(self)
        return super(Website, self).write(values)

    #----------------------------------------------------------
    # Page Management
    #----------------------------------------------------------
    @api.model
    def get_homepage(self, website_id):
        return self.browse(website_id).homepage_id.url

    @api.model
    def new_link(self, name, redirect_to):
        page = self.env['website.menu'].create({
            'name': name,
            'url': redirect_to,
            'website_id': self.get_current_website().id,
            'parent_id': self.browse(self.get_current_website().id).menu_id.id,
        })
        return page.id

    @api.model
    def new_page(self, name, add_menu=False, template='website.default_page', ispage=True, namespace=None, redirect_to=None):
        """ Create a new website page, and assign it a xmlid based on the given one
            :param name : the name of the page
            :param template : potential xml_id of the page to create
            :param namespace : module part of the xml_id if none, the template module name is used
        """
        # completely arbitrary max_length
        page_name = slugify(name, max_length=50)
        page_name = self.get_unique_path(page_name)

        template_record = self.env.ref(template)
        website_id = self._context.get('website_id')
        key = 'website.' + page_name
        view = template_record.copy({'website_id': website_id, 'key': key})
        
        view.with_context(lang=None).write({
            'page': ispage,
            'arch': template_record.arch.replace(template, page_name),
            'name': name,
        })
        page = self.env['website.page'].create({
            'name': name,
            'url': '/' + page_name,
            'website_ids': [(6, None, [self.get_current_website().id])],
            'ir_ui_view_id': view.id
        })
        if add_menu:
            self.env['website.menu'].create({
                'name': name,
                'url': '/' + page_name,
                'parent_id': self.browse(self.get_current_website().id).menu_id.id,
                'page_id': page.id,
                'website_id': self.get_current_website().id,
            })
        return '/' + page_name

    def get_unique_path(self, page_url):
        """ Given an url, return that url suffixed by counter if it already exists
            :param page_url : the url to be checked for uniqueness
        """
        if page_url.startswith('/'):
            page_url = page_url[1:]
        website_id = self.get_current_website().id
        inc = 0
        domain_static = ['|', ('website_ids', '=', False), ('website_ids', 'in', website_id)]
        page_temp = page_url
        while self.env['website.page'].with_context(active_test=False).sudo().search([('url', '=', '/' + page_temp)] + domain_static):
            inc += 1
            page_temp = page_url + (inc and "-%s" % inc or "")
        return page_temp

    def key_to_view_id(self, view_id):
        return self.env['ir.ui.view'].search([
            ('id', '=', view_id),
            '|', ('website_id', '=', self._context.get('website_id')), ('website_id', '=', False),
            ('page', '=', True),
            ('type', '=', 'qweb')
        ])

    @api.model
    def delete_object(self, object_id):
        """ Delete a page or a link, given its identifier
            :param object_id : object identifier eg: menu-5
        """
        model, id = object_id.split('-')
        if model == 'menu':
            # If we are deleting a menu (without a page)
            menu = self.env['website.menu'].browse(int(id))
            if menu:
                menu.unlink()
        elif model == 'page':
            # If we are deleting a page (that could possibly be a menu with a page)
            page = self.env['website.page'].browse(int(id))
            if page:
                # Check if it is a menu with a page and also delete menu if so
                menu = self.env['website.menu'].search([('page_id', '=', page.id)], limit=1)
                if menu:
                    menu.unlink()
                page.unlink()

    @api.model
    def page_search_dependencies(self, page_id=False):
        """ Search dependencies just for information. It will not catch 100%
            of dependencies and False positive is more than possible
            Each module could add dependences in this dict
            :returns a dictionnary where key is the 'categorie' of object related to the given
                view, and the value is the list of text and link to the resource using given page
        """
        dependencies = {}
        if not page_id:
            return dependencies

        page = self.env['website.page'].browse(int(page_id))
        website_id = self._context.get('website_id')

        url = page.url.replace("website.", "")
        fullurl = "/website.%s" % url[1:]
        
        # search for ir_ui_view (not from a website_page) with link
        page_search_dom = [
            '|', ('website_id', '=', website_id), ('website_id', '=', False),
            '|', ('arch_db', 'ilike', url), ('arch_db', 'ilike', fullurl)
        ]

        page_key = _('Page')
        views = self.env['ir.ui.view'].search(page_search_dom)
        for view in views:
            dependencies.setdefault(page_key, [])
            if not view.page:
                dependencies[page_key].append({
                    'text': _('Template <b>%s (id:%s)</b> contains a link to this page') % (view.key, view.id),
                    'link': '#'
                })

        # search for website_page with link
        website_page_search_dom = [
            '|', ('website_ids', 'in', website_id), ('website_ids', '=', False),
            '|', ('ir_ui_view_id.arch_db', 'ilike', url), ('ir_ui_view_id.arch_db', 'ilike', fullurl)
        ]
        pages = self.env['website.page'].search(website_page_search_dom)
        for page in pages:
            dependencies.setdefault(page_key, [])
            dependencies[page_key].append({
                'text': _('Page <b>%s</b> contains a link to this page') % page.url,
                'link': page.url
            })

        # search for menu with link
        menu_search_dom = [
            '|', ('website_id', '=', website_id), ('website_id', '=', False),
            '|', ('url', 'ilike', '%s' % url), ('url', 'ilike', '%s' % fullurl)
        ]

        menu_key = _('Menu')
        menus = self.env['website.menu'].search(menu_search_dom)
        for menu in menus:
            dependencies.setdefault(menu_key, []).append({
                'text': _('This page is in the menu <b>%s</b>') % menu.name,
                'link': False
            })
                
        return dependencies

    @api.model
    def page_exists(self, name, module='website'):
        try:
            name = (name or "").replace("/website.", "").replace("/", "")
            if not name:
                return False
            return self.env.ref('%s.%s' % module, name)
        except:
            return False

    #----------------------------------------------------------
    # Languages
    #----------------------------------------------------------

    @api.multi
    def get_languages(self):
        self.ensure_one()
        return self._get_languages()

    @tools.cache('self.id')
    def _get_languages(self):
        return [(lg.code, lg.name) for lg in self.language_ids]

    @api.multi
    def get_alternate_languages(self, req=None):
        langs = []
        if req is None:
            req = request.httprequest
        default = self.get_current_website().default_lang_code
        shorts = []

        def get_url_localized(router, lang):
            arguments = dict(request.endpoint_arguments)
            for key, val in list(arguments.items()):
                if isinstance(val, models.BaseModel):
                    arguments[key] = val.with_context(lang=lang)
            return router.build(request.endpoint, arguments)

        router = request.httprequest.app.get_db_router(request.db).bind('')
        for code, dummy in self.get_languages():
            lg_path = ('/' + code) if code != default else ''
            lg_codes = code.split('_')
            shorts.append(lg_codes[0])
            uri = get_url_localized(router, code) if request.endpoint else request.httprequest.path
            if req.query_string:
                uri += u'?' + req.query_string.decode('utf-8')
            lang = {
                'hreflang': ('-'.join(lg_codes)).lower(),
                'short': lg_codes[0],
                'href': req.url_root[0:-1] + lg_path + uri,
            }
            langs.append(lang)
        for lang in langs:
            if shorts.count(lang['short']) == 1:
                lang['hreflang'] = lang['short']
        return langs

    #----------------------------------------------------------
    # Utilities
    #----------------------------------------------------------

    @api.model
    def get_current_website(self):
        domain_name = request and request.httprequest.environ.get('HTTP_HOST', '').split(':')[0] or None
        website_id = self._get_current_website_id(domain_name)
        if request:
            request.context = dict(request.context, website_id=website_id)
        return self.browse(website_id)

    @tools.cache('domain_name')
    def _get_current_website_id(self, domain_name):
        """ Reminder : cached method should be return record, since they will use a closed cursor. """
        website = self.search([('domain', '=', domain_name)], limit=1)
        if not website:
            website = self.search([], limit=1)
        return website.id

    @api.model
    def is_publisher(self):
        return self.env['ir.model.access'].check('ir.ui.view', 'write', False)

    @api.model
    def is_user(self):
        return self.env['ir.model.access'].check('ir.ui.menu', 'read', False)

    @api.model
    def get_template(self, template):
        View = self.env['ir.ui.view']
        if isinstance(template, pycompat.integer_types):
            view_id = template
        else:
            if '.' not in template:
                template = 'website.%s' % template
            view_id = View.get_view_id(template)
        if not view_id:
            raise NotFound
        return View.browse(view_id)

    @api.model
    def pager(self, url, total, page=1, step=30, scope=5, url_args=None):
        return pager(url, total, page=page, step=step, scope=scope, url_args=url_args)

    def rule_is_enumerable(self, rule):
        """ Checks that it is possible to generate sensible GET queries for
            a given rule (if the endpoint matches its own requirements)
            :type rule: werkzeug.routing.Rule
            :rtype: bool
        """
        endpoint = rule.endpoint
        methods = endpoint.routing.get('methods') or ['GET']

        converters = list(rule._converters.values())
        if not ('GET' in methods
            and endpoint.routing['type'] == 'http'
            and endpoint.routing['auth'] in ('none', 'public')
            and endpoint.routing.get('website', False)
            and all(hasattr(converter, 'generate') for converter in converters)
            and endpoint.routing.get('website')):
            return False

        # dont't list routes without argument having no default value or converter
        spec = inspect.getargspec(endpoint.method.original_func)

        # remove self and arguments having a default value
        defaults_count = len(spec.defaults or [])
        args = spec.args[1:(-defaults_count or None)]

        # check that all args have a converter
        return all((arg in rule._converters) for arg in args)

    @api.multi
    def enumerate_pages(self, query_string=None, hide_unindexed_pages=False, hide_unpublished_pages=True):
        """ Available pages in the website/CMS. This is mostly used for links
            generation and can be overridden by modules setting up new HTML
            controllers for dynamic pages (e.g. blog).
            By default, returns template views marked as pages.
            :param str query_string: a (user-provided) string, fetches pages
                                     matching the string
            :returns: a list of mappings with two keys: ``name`` is the displayable
                      name of the resource (page), ``url`` is the absolute URL
                      of the same.
            :rtype: list({name: str, url: str})
        """
        router = request.httprequest.app.get_db_router(request.db)
        # Force enumeration to be performed as public user
        url_set = set()
        for rule in router.iter_rules():
            if not self.rule_is_enumerable(rule):
                continue
            converters = rule._converters or {}
            if query_string and not converters and (query_string not in rule.build([{}], append_unknown=False)[1]):
                continue
            values = [{}]
            # converters with a domain are processed after the other ones
            convitems = sorted(
                converters.items(),
                key=lambda x: hasattr(x[1], 'domain') and (x[1].domain != '[]'))
            for (i, (name, converter)) in enumerate(convitems):
                newval = []
                for val in values:
                    query = i == len(convitems)-1 and query_string
                    for value_dict in converter.generate(uid=self.env.uid, query=query, args=val):
                        newval.append(val.copy())
                        value_dict[name] = value_dict['loc']
                        del value_dict['loc']
                        newval[-1].update(value_dict)
                values = newval

            for value in values:
                domain_part, url = rule.build(value, append_unknown=False)
                page = {'loc': url}
                for key, val in value.items():
                    if key.startswith('__'):
                        page[key[2:]] = val
                if url in ('/sitemap.xml',):
                    continue
                if url in url_set:
                    continue
                url_set.add(url)

                yield page

        # '/' already has a http.route & is in the routing_map so it will already have an entry in the xml
        domain = [('url', '!=', '/')]
        if hide_unindexed_pages:
            domain += [('website_indexed', '=', True)]
        if hide_unpublished_pages:
            domain += [('website_published', '=', True)]
        if query_string:
            domain += [('url', 'like', query_string)]

        pages = self.get_website_pages(domain)
        for page in pages:
            record = {'loc': page['url']}
            if page.ir_ui_view_id and page.ir_ui_view_id.priority != 16:
                record['priority'] = min(round(page.ir_ui_view_id.priority / 32.0, 1), 1)
            if page['write_date']:
                record['lastmod'] = page['write_date'][:10]
            yield record

    @api.multi
    def get_website_pages(self, domain=[], order='name', limit=None):
        domain += ['|', ('website_ids', 'in', self.get_current_website().id), ('website_ids', '=', False)]
        pages = request.env['website.page'].search(domain, order='name', limit=limit)
        return pages

    @api.multi
    def search_pages(self, needle=None, limit=None):
        name = re.sub(r"^/p(a(g(e(/(w(e(b(s(i(t(e(\.)?)?)?)?)?)?)?)?)?)?)?)?", "", needle or "")
        name = slugify(name, max_length=50)
        res = []
        for page in self.enumerate_pages(query_string=name, hide_unpublished_pages=False):
            res.append(page)
            if len(res) == limit:
                break
        return res

    @api.model
    def image_url(self, record, field, size=None):
        """ Returns a local url that points to the image field of a given browse record. """
        sudo_record = record.sudo()
        sha = hashlib.sha1(getattr(sudo_record, '__last_update').encode('utf-8')).hexdigest()[0:7]
        size = '' if size is None else '/%s' % size
        return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)

    @api.model
    def get_cdn_url(self, uri):
        # Currently only usable in a website_enable request context
        if request and request.website and not request.debug and request.website.user_id.id == request.uid:
            cdn_url = request.website.cdn_url
            cdn_filters = (request.website.cdn_filters or '').splitlines()
            for flt in cdn_filters:
                if flt and re.match(flt, uri):
                    return urls.url_join(cdn_url, uri)
        return uri

    @api.model
    def action_dashboard_redirect(self):
        if self.env.user.has_group('base.group_system') or self.env.user.has_group('website.group_website_designer'):
            return self.env.ref('website.backend_dashboard').read()[0]
        return self.env.ref('website.action_website').read()[0]


class SeoMetadata(models.AbstractModel):

    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    website_meta_title = fields.Char("Website meta title", translate=True)
    website_meta_description = fields.Text("Website meta description", translate=True)
    website_meta_keywords = fields.Char("Website meta keywords", translate=True)


class WebsitePublishedMixin(models.AbstractModel):

    _name = "website.published.mixin"

    website_published = fields.Boolean('Visible in Website', copy=False)
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    @api.multi
    def _compute_website_url(self):
        for record in self:
            record.website_url = '#'

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.env.user.has_group('website.group_website_publisher') and self.website_url != '#':
            return self.open_website_url()
        return self.write({'website_published': not self.website_published})

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }


class Page(models.Model):
    _name = "website.page"
    _inherit = ["website.published.mixin"]
    _description = "Page"

    name = fields.Char('Page Name')
    url = fields.Char('Page Url')
    website_ids = fields.Many2many('website', string='Websites')
    ir_ui_view_id = fields.Many2one('ir.ui.view', string='View')
    website_indexed = fields.Boolean('Page Indexed', default=True)
    date_publish = fields.Datetime('Published Date')

    @api.multi
    def unlink(self):
        """ When a website_page is deleted, the ORM does not delete its ir_ui_view.
            So we got to delete it ourself, but only if the ir_ui_view is not used by another website_page.
        """
        # Second, handle it's ir_ui_view
        for page in self:
            # Other pages linked to the ir_ui_view of the page being deleted (will it even be possible?)
            pages_linked_to_iruiview = self.env['website.page'].search(
                [('ir_ui_view_id', '=', self.ir_ui_view_id.id), ('id', '!=', self.id)]
            )
            if len(pages_linked_to_iruiview) == 0:
                # If there is no other pages linked to that ir_ui_view, we can delete the ir_ui_view
                self.env['ir.ui.view'].search([('id', '=', self.ir_ui_view_id.id)]).unlink()
        # And then delete the website_page itself
        return super(Page, self).unlink()

    @api.model
    def get_pages_not_in_menu(self, website_id):
        pages_in_menu = self.env['website.menu'].search([('website_id', '=', website_id)]).mapped('url')
        pages_domain = ['|', ('website_ids', 'in', website_id), ('website_ids', '=', False)]
        pages_domain += [('url', 'not in', pages_in_menu)]
        pages = self.search_read(pages_domain, fields=['id', 'name', 'url', 'website_published', 'date_publish'], order='url')
        for page in pages:
            page['id'] = 'page-' + str(page['id'])
        return {
            'pages': pages,
        }

    @api.model
    def get_object(self, id, website_id):
        model, id = id.split('-')
        if model == 'menu':
            domain = [('website_id', '=', website_id), ('id', '=', id)]
            item = self.env['website.menu'].search(domain, limit=1)
            if item.page_id:
                item = self.search_read([('id', '=', item.page_id.id)], fields=['id', 'name', 'url', 'website_published', 'date_publish'], limit=1)
                item[0]['model'] = 'Page'
                item[0]['is_menu'] = True
                item[0]['id'] = 'page-' + str(item[0]['id'])
            else:
                item = self.env['website.menu'].search_read(domain, fields=['id', 'name', 'url', 'website_published', 'date_publish'], limit=1)
                item[0]['model'] = 'Link'
                item[0]['is_menu'] = True
                item[0]['id'] = 'menu-' + str(item[0]['id'])
        else:
            domain = ['|', ('website_ids', 'in', website_id), ('website_ids', '=', False), ('id', '=', id)]
            item = self.search_read(domain, fields=['id', 'name', 'url', 'website_published', 'date_publish'], limit=1)
            item[0]['model'] = 'Page'
            item[0]['is_menu'] = False
            item[0]['id'] = 'page-' + str(item[0]['id'])

        return item

    @api.model
    def save_page_info(self, website_id, data):
        model, id = data['id'].split('-')
        if model == 'menu':
            # If the website.menu is not in menu anymore:
            if not data['is_menu']:
                # Just delete it
                self.env['website.menu'].browse(int(id)).unlink()
            else:
                self.env['website.menu'].browse(int(id)).write({'name': data['name'], 'url': data['url']})
        elif model == 'page':
            if data['is_homepage']:
                # If page is set as the new homepage, set it on website (only page can be set as homepage)
                self.env['website'].browse(self.env['website'].get_current_website().id).write({'homepage_id': id})
            else:
                # If the page is not a homepage, check if it was the homepage
                if self.env['website'].browse(self.env['website'].get_current_website().id).homepage_id.id == int(id):
                    self.env['website'].browse(self.env['website'].get_current_website().id).write({'homepage_id': None})
            menu = self.env['website.menu'].search([('page_id', '=', int(id))])
            if not data['is_menu']:
                #If the page is no longer in menu, we should remove its website_menu
                if menu:
                    menu.unlink()
            else:
                #The page is now a menu, check if has already one
                if menu:
                    menu.write({'name': data['name'], 'url': data['url']})
                else:
                    self.env['website.menu'].create({
                        'name': data['name'],
                        'url': data['url'],
                        'page_id': id,
                        'parent_id': self.env['website'].browse(website_id).menu_id.id,
                        'website_id': self.env['website'].get_current_website().id,
                    })
            # self.browse(int(id)).write({'name': data['name'], 'url': data['url'], 'website_published': data['website_published'], 'date_publish': data['date_publish']})
            self.browse(int(id)).write({'name': data['name'], 'url': data['url'], 'website_published': data['website_published']})
        return True

    @api.model
    def clone_object(self, object_id):
        """ Clone a page, given its identifier
            :param page_id : website.page identifier
        """
        def clone_page(page):
            new_page = page.copy({'name': page.name + ' (copy)'})
            # Copy the page's ir_ui_view or the cloned page will be linked to the same ir_ui_view
            new_path = self.env['website'].get_unique_path(page.url)
            view = self.env['ir.ui.view'].browse(page.ir_ui_view_id.id)
            new_view = view.copy()
            new_page.write({
                'url': '/' + new_path,
                'ir_ui_view_id': new_view.id
            })
            return new_page

        model, id = object_id.split('-')
        if model == 'menu':
            menu = self.env['website.menu'].browse(int(id))
            if menu:
                # If the cloned element is a link (menu without a page), no point to redirect to its url,
                # just reload the page (to redraw menu & page management)
                menu.copy({'name': menu.name + ' (copy)'})
                return ""
        elif model == 'page':
            page = self.env['website.page'].browse(int(id))
            new_page = clone_page(page)
            
            menu = self.env['website.menu'].search([('page_id', '=', page.id)], limit=1)
            if menu:
                # If the cloned element is a menu having a page
                new_menu = menu.copy()
                new_menu.write({'url': new_page.url, 'name': menu.name + ' (copy)', 'page_id': new_page.id})
                
            return new_page.url + '?enable_editor=1'


class Menu(models.Model):

    _name = "website.menu"
    _description = "Website Menu"

    _parent_store = True
    _parent_order = 'sequence'
    _order = "sequence"

    def _default_sequence(self):
        menu = self.search([], limit=1, order="sequence DESC")
        return menu.sequence or 0

    name = fields.Char('Menu', required=True, translate=True)
    url = fields.Char('Url', default='')

    page_id = fields.Many2one('website.page', 'Related Page')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer(default=_default_sequence)
    website_id = fields.Many2one('website', 'Website')  # TODO: support multiwebsite once done for ir.ui.views
    parent_id = fields.Many2one('website.menu', 'Parent Menu', index=True, ondelete="cascade")
    child_id = fields.One2many('website.menu', 'parent_id', string='Child Menus')
    parent_left = fields.Integer('Parent Left', index=True)
    parent_right = fields.Integer('Parent Rigth', index=True)

    # would be better to take a menu_id as argument
    @api.model
    def get_tree(self, website_id, menu_id=None):
        def make_tree(node):
            menu_node = dict(
                id='menu-' + str(node.id),
                name=node.name,
                url=node.url,
                
                new_window=node.new_window,
                sequence=node.sequence,
                parent_id=node.parent_id.id,
                is_menu=True,
                children=[],
                is_link=False if node.page_id.id else True,
                website_published=node.page_id.website_published if node.page_id.website_published else False,
                date_publish=node.page_id.date_publish if node.page_id.date_publish else False,
            )
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node
        if menu_id:
            menu = self.browse(menu_id)
        else:
            menu = self.env['website'].browse(website_id).menu_id
        return make_tree(menu)

    @api.model
    def save(self, website_id, data):
        def replace_id(old_id, new_id):
            for menu in data['data']:
                if menu['id'] == old_id:
                    menu['id'] = new_id
                if menu['parent_id'] == old_id:
                    menu['parent_id'] = new_id
                    
        def transform_id(id):
            return id.split('-')[1]

        # First level menus won't have a parent_id, we should give them the website root menu's id
        for elem in data['data']:
            if 'parent_id' not in elem:
                elem['parent_id'] = self.env['website'].browse(website_id).menu_id.id
                
        # Create a menu holding the page if it is a page that is now becoming a menu
        for elem in data['data']:
            if 'is_menu' not in elem or not elem['is_menu']:
                real_menu = self.env['website.menu'].create({
                    'name': elem['name'],
                    'url': elem['url'],
                    'page_id': elem['id'].split('-')[1],
                    'parent_id': self.env['website'].browse(website_id).menu_id.id,
                    'website_id': self.env['website'].get_current_website().id,
                })
                # Replace the item ID (which is the page one) by the newly created menu's for the incoming hierarchy creation
                replace_id(elem['id'], real_menu.id)
                elem['id'] = real_menu.id
        
        # Transform the ID 'menu-XX' to XX
        for elem in data['data']:
            if isinstance(elem['id'], basestring):
                elem['id'] = elem['id'].split('-')[1]
            if isinstance(elem['parent_id'], basestring):
                elem['parent_id'] = elem['parent_id'].split('-')[1]

            self.browse(int(elem['id'])).write(elem)
            
        # Delete menu that were drag & droped to "other pages"
        # This loop has to be the last or deleting a parent menu will delete its child (cascade) that
        # shouldn't be deleted
        if data['to_delete']:
            # Get the ID XX from 'menu-XX'
            test = [unslug(elem)[1] for elem in data['to_delete']]
            self.browse(test).unlink()
            
        return True


class WebsiteRedirect(models.Model):
    _name = "website.redirect"
    _description = "Website Redirect"
    _order = "sequence"

    comment = fields.Char('Redirect Comment')
    type = fields.Selection([('301', 'Moved permanently'), ('302', 'Moved temporarily')], string='Redirection Type')
    url_from = fields.Char('Redirect From')
    url_to = fields.Char('Redirect To')
    website_id = fields.Many2one('website', 'Website')
    active = fields.Boolean(default=True)
    
    def _default_sequence(self):
        menu = self.search([], limit=1, order="sequence DESC")
        return menu.sequence or 0
    sequence = fields.Integer(default=_default_sequence)
