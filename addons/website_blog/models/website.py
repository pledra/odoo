# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Website(models.Model):
    _inherit = "website"

    @api.model
    def page_search_dependencies(self, object_id):
        dep = super(Website, self).page_search_dependencies(object_id)

        model, id = object_id.split('-')
        if model == 'page':
            page = self.env['website.page'].browse(int(id))
            path = page.path.replace("website.", "")
            fullpath = "/website.%s" % path[1:]

            dom = [
                '|', ('content', 'ilike', path), ('content', 'ilike', fullpath)
            ]
            posts = self.env['blog.post'].search(dom)
            if posts:
                page_key = _('Blog Post')
                dep[page_key] = []
            for p in posts:
                dep[page_key].append({
                    'text': _('Blog Post <b>%s</b> seems to have a link to this page !') % p.name,
                    'link': p.website_url
                })

        return dep
