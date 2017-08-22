# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
import hashlib
import re

from werkzeug import urls
from werkzeug.exceptions import NotFound

from odoo import api, fields, models, tools
from odoo.addons.http_routing.models.ir_http import slugify
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
    menu_ids = fields.Many2many('website.page', compute='_compute_menu', string='Main Menu')
    favicon = fields.Binary(string="Website Favicon", help="This field holds the image used to display a favicon on the website.")

    @api.multi
    def _compute_menu(self):
        for website in self:
            website.menu_ids = self.env['website.page'].with_context(active_test=False).sudo().search([('parent_id', '=', False), ('is_menu', '=', True), '|', ('website_ids', '=', False), ('website_ids', 'in', website.id)], order='sequence')

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
    def new_link(self, name, redirect_to):
        page = self.env['website.page'].create({
            'name': name,
            'path': redirect_to,
            'website_ids': [(6, None, [self.get_current_website().id])],
            'type': 'qweb',
            'page': False,
            'is_menu': True
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
        
        self.env['website.page'].create({
            'name': name if name else 'Home', # particular case where user click on create page on 404 as admin on / page
            'path': '/' + page_name,
            'arch': template_record.arch.replace(template, page_name if name else 'Home'), # particular case where user click on create page on 404 as admin on / page
            'website_ids': [(6, None, [self.get_current_website().id])],
            'type': 'qweb',
            'page': ispage,
            'is_menu': add_menu
        })
        return '/' + page_name
        
    def get_unique_path(self, page_name):
        if page_name.startswith('/'):
            page_name = page_name[1:]
        website_id = self.get_current_website().id
        inc = 0
        domain_static = [('website_ids', '=', False), ('website_ids', 'in', website_id)]
        page_temp = page_name
        while self.env['website.page'].with_context(active_test=False).sudo().search([('path', '=', '/' + page_temp), '|'] + domain_static):
            inc += 1
            page_temp = page_name + (inc and "-%s" % inc or "")
        return page_temp

    def key_to_view_id(self, view_id):
        return self.env['ir.ui.view'].search([
            ('id', '=', view_id),
            '|', ('website_id', '=', self._context.get('website_id')), ('website_id', '=', False),
            ('page', '=', True),
            ('type', '=', 'qweb')
        ])

    @api.model
    def delete_page(self, view_id):
        """ Delete a page, given its identifier
            :param view_id : website.page identifier
        """
        page = self.env['website.page'].browse(view_id)
        if page:
            page.unlink()
            
    

    @api.model
    def rename_page(self, view_id, new_name):
        """ Change the name of the given page
            :param view_id : id of the view to rename
            :param new_name : name to use
        """
        page = self.env['website.page'].browse(view_id)
        if page:
            # slugify the new name
            page_name = slugify(new_name, max_length=50)
            page_name = self.get_unique_path(page_name)
            page.write({
                'path': '/' + page_name,
                'name': new_name,
                'arch_db': page.arch_db.replace(slugify(page.name), page_name, 1)
            })
            return page_name
        return False

    @api.model
    def page_search_dependencies(self, view_id=False):
        """ Search dependencies just for information. It will not catch 100%
            of dependencies and False positive is more than possible
            Each module could add dependences in this dict
            :returns a dictionnary where key is the 'categorie' of object related to the given
                view, and the value is the list of text and link to the resource using given page
        """
        dependencies = {}
        if not view_id:
            return dependencies

        page = self.env['website.page'].browse(view_id)

        website_id = self._context.get('website_id')

        path = page.path.replace("website.", "")
        fullpath = "/website.%s" % path[1:]

        if page.page:
            # search for ir_ui_view (not from a website_page) with link
            page_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('arch_db', 'ilike', path), ('arch_db', 'ilike', fullpath)
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
                '|', ('arch_db', 'ilike', path), ('arch_db', 'ilike', fullpath)
            ]
            pages = self.env['website.page'].search(website_page_search_dom)
            for page in pages:
                dependencies.setdefault(page_key, [])
                dependencies[page_key].append({
                    'text': _('Page <b>%s</b> contains a link to this page') % page.path,
                    'link': page.path
                })

            # search for menu with link
            menu_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('path', '=', path), ('path', '=', fullpath),
                ('is_menu', '=', True)
            ]

            menu_key = _('Menu')
            pages_menu = self.env['website.page'].search(menu_search_dom)
            for page in pages_menu:
                dependencies.setdefault(menu_key, []).append({
                    'text': _('This page is in the menu <b>%s</b>') % page.name,
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
    def enumerate_pages(self, query_string=None, hide_unindexed_pages=False):
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
        domain = [('path', '!=', '/'), ('website_published', '=', True)]
        if hide_unindexed_pages:
            domain += [('website_indexed', '=', True)]

        pages = self.get_website_pages(domain)
        for page in pages:
            record = {'loc': page['path']}
            if page['priority'] != 16:
                record['priority'] = min(round(page['priority'] / 32.0, 1), 1)
            if page['write_date']:
                record['lastmod'] = page['write_date'][:10]
            yield record

    @api.multi
    def get_website_pages(self, domain=[], order='name', limit=None):
        Page = request.env['website.page']
        website = request.env['website'].get_current_website()
        domain += [('page', '=', True), '|', ('website_ids', 'in', website.id), ('website_ids', '=', False)]
        pages = Page.search(domain, order='name', limit=limit)
        return pages

    @api.multi
    def search_pages(self, needle=None, limit=None):
        name = re.sub(r"^/p(a(g(e(/(w(e(b(s(i(t(e(\.)?)?)?)?)?)?)?)?)?)?)?)?", "", needle or "")
        name = slugify(name, max_length=50)
        res = []
        for page in self.enumerate_pages(query_string=name):
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


#rde
class Page(models.Model):
    _name = "website.page"
    _inherits = {'ir.ui.view': 'ir_ui_view_id'}
    _inherit = ["website.published.mixin"]
    _description = "Page"

    ir_ui_view_id = fields.Many2one('ir.ui.view', string='View', required=True, ondelete="cascade")
    website_ids = fields.Many2many('website', string='Websites')
    path = fields.Char('Page Path')
    website_indexed = fields.Boolean('Page indexed', default=True)

    @api.multi
    def unlink(self):
        #will it be possible to have a website record pointing to an ir_ui_view from odoo (not a website one) or it does not make sense ?
        #if yes, we somehow have to check that we can delete the ir_ui_view record (page true ?)
        for page in self:
            pages_linked_to_iruiview = self.env['website.page'].search(
                [('ir_ui_view_id', '=', self.ir_ui_view_id.id), ('id', '!=', self.id)]
            )
            if len(pages_linked_to_iruiview) == 0:
                self.env['ir.ui.view'].search([('id', '=', self.ir_ui_view_id.id)]).unlink()
        return super(Page, self).unlink()

    @api.model
    def get_pages(self, website_id):
        pages_domain = ['|', ('website_ids', 'in', website_id), ('website_ids', '=', False)]
        pages_domain += [('parent_id', '=', None), ('is_menu', '=', False)]
        pages = self.search_read(pages_domain, fields=['path', 'website_published', 'name', 'page', 'parent_id', 'is_homepage', 'is_menu', 'website_meta_title', 'website_meta_keywords', 'website_meta_description'], order='path')
        return {
            'pages': pages,
        }
        
    @api.model
    def get_homepage(self, website_id):
        pages_domain = ['|', ('website_ids', 'in', website_id), ('website_ids', '=', False)]
        pages_domain += [('is_homepage', '=', True)]
        page = self.search(pages_domain, order='sequence', limit=1)
        return page

    @api.model
    def get_page_from_path(self, path, website_id):
        #menu_domain = ['|', ('website_id', '=', website_id), ('website_id', '=', False), ('url', '=', path)]
        #menu = self.env['website.menu'].search(menu_domain, limit=1)

        pages_domain = ['|', ('website_ids', 'in', website_id), ('website_ids', '=', False), ('path', '=', path)]
        page = self.search_read(pages_domain, fields=['name', 'website_indexed', 'path', 'page', 'is_menu', 'is_homepage', 'website_meta_title', 'website_meta_keywords', 'website_meta_description'], limit=1)
        return page

    @api.model
    def save_page_info(self, website_id, data):
        # if page is not in menu anymore, be sure that it has no children anymore (or they wont be display in the "other page" list)
        # because "other page" list is a 1 level list only (menu page is a 2 nested level list)
        if not data['is_menu']:
            self.search(['|', ('website_ids', 'in', website_id), ('website_ids', '=', False), ('parent_id', '=', data['id'])]).write({'parent_id': None})
            # As the page is not a menu anymore, unlink it from its parent that may still be a menu
            data['parent_id'] = None
        # if page is set as homepage, remove the previous homepage
        if 'is_homepage' in data and data['is_homepage']:
            self.search(['|', ('website_ids', 'in', website_id), ('website_ids', '=', False), ('is_homepage', '=', True)]).write({'is_homepage': False})
        
        self.browse(data['id']).write(data)
        return True
        
    @api.model
    def clone_page(self, page_id):
        """ Clone a page, given its identifier
            :param page_id : website.page identifier
        """
        page = self.env['website.page'].browse(page_id)
        new_page = page.copy()
        #rec = super(Page, page).copy()
        new_path = self.env['website'].get_unique_path(page.path)
        new_name = page.name + ' (clone)'
        new_page.write({
            'path': '/' + new_path,
            'name': new_name,
            'is_homepage': False
        })
        return new_path
            
    # ------- MENU ------- #
    _parent_store = True
    _parent_order = 'sequence'
    _order = "sequence"

    def _default_sequence(self):
        menu = self.search([], limit=1, order="sequence DESC")
        return menu.sequence or 0

    is_menu = fields.Boolean('Show in menu', default=True)
    is_homepage = fields.Boolean('Website home page', default=False)
    #menu_name = fields.Char('Menu Entry')
    new_window = fields.Boolean('New Window', default=False)
    sequence = fields.Integer(default=_default_sequence)
    parent_id = fields.Many2one('website.page', 'Parent Menu', index=True, ondelete="set null")
    child_id = fields.One2many('website.page', 'parent_id', string='Child Menus')
    parent_left = fields.Integer('Parent Left', index=True)
    parent_right = fields.Integer('Parent Rigth', index=True)

    # would be better to take a menu_id as argument
    @api.model
    def get_tree(self, website_id, menu_id=None):
        #import pudb;pu.db
        def make_tree(node):
            menu_node = dict(
                id=node.id,
                name=node.name,
                path=node.path,
                page=node.page,
                new_window=node.new_window,
                sequence=node.sequence,
                is_menu=node.is_menu,
                is_homepage=node.is_homepage,
                parent_id=node.parent_id.id,
                children=[],
                model='website.page'
            )
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node
        return_node = []
        menus = self.env['website'].browse(website_id).menu_ids
        for menu in menus:
            return_node.append(make_tree(menu))
        return return_node

    @api.model
    def save_tree_menu(self, website_id, data):
        def replace_id(old_id, new_id):
            for menu in data['data']:
                if menu['id'] == old_id:
                    menu['id'] = new_id
                if menu['parent_id'] == old_id:
                    menu['parent_id'] = new_id
        
        #import pudb;pu.db
        #TODO: somehow send to_delete array so we can browse on just ID to remove not all
        #I can think of 2 ways in JS: compare menu array before (load_page_management_menu) 
        #and when click on save and ID in first but not in second array are to delete
        to_delete = data['to_delete']
        if to_delete:
            self.browse(to_delete).write({'is_menu': False, 'parent_id': None})
        #self.search([]).write({'is_menu': False, 'parent_id': None})
        
        for menu in data['data']:
            if 'parent_id' not in menu:
                menu['parent_id'] = None
            mid = menu['id']
            if isinstance(mid, basestring):
                new_menu = self.create({'name': menu['name']})
                replace_id(mid, new_menu.id)
        for menu in data['data']:
            if 'parent_id' not in menu:
                menu['parent_id'] = None
            menu['is_menu'] = True
            self.browse(menu['id']).write(menu)
        return True
        
