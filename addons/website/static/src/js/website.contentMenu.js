odoo.define('website.contentMenu', function (require) {
"use strict";

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var widget = require('web_editor.widget');
var website = require('website.website');
var websiteSeo = require('website.seo');

var _t = core._t;
var qweb = core.qweb;

ajax.loadXML('/website/static/src/xml/website.contentMenu.xml', qweb);

var TopBarContent = Widget.extend({
    events: {
        "click .js_delete_page": "delete_page",
        "click .js_clone_page": "clone_page",
        "click .js_save_page_info": "save_page_info",
        "click .js_load_page_info": "load_page_info",
        "click .js_close_page_info": "close_page_info",
        "click a.js_add_menu": "add_menu"
    },
    start: function () {
        var self = this;
        self.to_delete = [];
        self.websiteSeoConfig = null;
        // Add page modal + menu content event
        this.$el.add($('#o_website_add_page_modal')).on('click', 'a[data-action], button[data-action]', function (e) {
            e.preventDefault();
            self[$(this).data('action')]();
        });
        self.load_page_management_menu().then(function(e){
            $('#pages_management_menu_pages').nestedSortable({
                listType: 'ul',
                handle: 'div',
                items: 'li',
                maxLevels: 2,
                toleranceElement: '> div',
                forcePlaceholderSize: true,
                opacity: 0.6,
                placeholder: 'oe_menu_placeholder',
                tolerance: 'pointer',
                attribute: 'data-menu-id',
                expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
                connectWith: '#pages_management_other_pages',
                receive: function(event, ui) { 
                    var id = $(ui.item).data('menu-id');
                    var index = self.to_delete.indexOf(+id);
                    if(index)
                        self.to_delete.splice(index, 1);
                },
            });
            $('#pages_management_other_pages').nestedSortable({
                listType: 'ul',
                handle: 'div',
                items: 'li',
                maxLevels: 1,
                toleranceElement: '> div',
                forcePlaceholderSize: true,
                opacity: 0.6,
                placeholder: 'oe_menu_placeholder',
                tolerance: 'pointer',
                attribute: 'data-menu-id',
                expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
                connectWith: '#pages_management_menu_pages',
                receive: function(event, ui) { self.to_delete.push($(ui.item).data('menu-id'));},
            });
            
            if (location.search.indexOf("spm") > -1)
                self.open_management_page_menu();
        });
    },
    load_page_management_menu: function () {
        var context = base.get_context();
        var def = $.Deferred();
        def.resolve(null);
        var self = this;
        return def.then(function (root_id) {
            return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.page',
                method: 'get_pages',
                args: [context.website_id],
                kwargs: {
                    context: context
                },
            }).then(function (result) {
                return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                    model: 'website.page',
                    method: 'get_tree',
                    args: [context.website_id],
                    kwargs: {
                        context: context
                    },
                }).then(function (menu) {
                    self.menus = menu;
                    self.root_menu_id = menu.id;
                    self.flat = self.flatenize(menu);
                    self.flat = self.flatenize(result.pages, self.flat);
                    $(qweb.render('website.pagesMenu', {pages: result.pages, tree_menu:menu, page_url: window.location.pathname})).appendTo(".oe_page_management_menu");
                });
            });
        });
    },
    open_management_page_menu: function(){
        this.$el.toggleClass('open');
    },
    save_management_page_menu: function(){
        var self = this;
        var new_menu = this.$('#pages_management_menu_pages').nestedSortable('toArray', {startDepthCount: 0});
        var levels = [];
        var data = [];
        var context = base.get_context();
        // Resequence, re-tree and remove useless data
        new_menu.forEach(function (menu) {
            if (menu.id) {
                levels[menu.depth] = (levels[menu.depth] || 0) + 1;
                var mobj = self.flat[menu.id];
                mobj.sequence = levels[menu.depth];
                mobj.parent_id = (menu.parent_id|0) || menu.parent_id || self.root_menu_id;
                delete(mobj.children);
                data.push(mobj);
            }
        });       
        
        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'website.page',
            method: 'save_tree_menu',
            args: [[context.website_id], { data: data, to_delete: self.to_delete }],
            kwargs: {
                context: context
            },
        }).then(function () {
            //Redraw menu
            editor.reload();
        });
        
    },
    load_page_info: function(ev){
        var self = this;
        var context = base.get_context();
        var def = $.Deferred();
        def.resolve(null);
        return def.then(function (root_id) {
            return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.page',
                method: 'get_page_from_path',
                args: [$(ev.currentTarget).data('page-path'),context.website_id],
                kwargs: {
                    context: context
                },
            }).then(function (page) {
                $(".oe_page_management_page_info").html($(qweb.render('website.pagesMenu.page_info', {page: page[0], server_url:window.location.origin})));
                self.websiteSeoConfig = new websiteSeo.Configurator(self, {page: page[0],model: $(ev.currentTarget).data('model')});
                self.websiteSeoConfig.appendTo($('#seo_promote'));
                $(".oe_page_management_page_info").show();
                $("button[data-action='save_management_page_menu']").prop('disabled', true);
            });
        });
    },
    close_page_info: function(ev){
        $(".oe_page_management_page_info").hide();
        $("button[data-action='save_management_page_menu']").prop('disabled', false);
    },
    save_page_info: function(ev){
        var self = this;
        var context = base.get_context();
        var page_name = $(".oe_page_management_page_info #page_name").val();
        var page_path = $(".oe_page_management_page_info #page_path").val();
        var is_menu = $(".oe_page_management_page_info #is_menu").prop('checked');
        var is_homepage = $(".oe_page_management_page_info #is_homepage").prop('checked');
        var website_meta_title = $(".oe_page_management_page_info input[name=seo_page_title]").val();
        var website_meta_description = $('.oe_page_management_page_info textarea[name=seo_page_description]').val();
        var data = {
            name: page_name, 
            path: page_path,
            is_menu: is_menu,
            is_homepage: is_homepage,
            id: $(ev.currentTarget).data('id'),
            website_meta_title: website_meta_title,
            website_meta_description: website_meta_description,
        }
        //ES6: Object.assign(seo_fields, this.websiteSeoConfig.get_fields());
        var seo_fields = this.websiteSeoConfig.get_fields();
        for (var attrname in seo_fields) { data[attrname] = seo_fields[attrname]; }
        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'website.page',
            method: 'save_page_info',
            args: [[context.website_id], data],
            kwargs: {
                context: context
            },
        }).then(function () {
            //Redirect to the modified page
            window.location = page_path + '?spm=1'
            //Just some not very usefull ui but help user to see it is working
            $(".oe_page_management_page_info").hide();
            $("button[data-action='save_management_page_menu']").prop('disabled', false);
        });
    },
    flatenize: function (nodes, dict) {
        dict = dict || {};
        var self = this;
        nodes.forEach(function(node){
            dict[node.id] = node;
            if(typeof node.children === 'undefined')
                node.children = [];
            node.children.forEach(function (child) {
                self.flatenize([child], dict);
            });
        });
        
        return dict;
    },
    new_page: function () {
        website.prompt({
            id: "editor_new_page",
            window_title: _t("New Page"),
            input: _t("Page Title"),
            init: function () {
                var $group = this.$dialog.find("div.form-group");
                $group.removeClass("mb0");

                var $add = $('<div/>', {'class': 'form-group mb0'})
                            .append($('<span/>', {'class': 'col-sm-offset-3 col-sm-9 text-left'})
                                    .append(qweb.render('web_editor.components.switch', {id: 'switch_addTo_menu', label: _t("Add page in menu")})));
                $add.find('input').prop('checked', true);
                $group.after($add);
            }
        }).then(function (val, field, $dialog) {
            if (val) {
                var url = '/website/add/' + encodeURIComponent(val);
                if ($dialog.find('input[type="checkbox"]').is(':checked')) url +="?add_menu=1";
                document.location = url;
            }
        });
    },
    clone_page: function(ev){
        var self = this;
        var context = base.get_context();
        self.mo_id = $(ev.currentTarget).data('id');
        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'website.page',
            method: 'clone_page',
            args: [self.mo_id],
            kwargs: {
                context: context,
            },
        }).then(function (path) {
            window.location = path + '?spm=1';
        });
    },
    delete_page: function (ev) {
        var self = this;
        var context = base.get_context();
        self.mo_id = $(ev.currentTarget).data('id');

        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'website',
            method: 'page_search_dependencies',
            args: [self.mo_id],
            kwargs: {
                context: context,
            },
        }).then(function (deps) {
            website.prompt({
                id: "editor_delete_page",
                window_title: _t("Delete Page"),
                dependencies: deps,
                    init: function () { $('.btn-continue').prop("disabled", true); },
            }, 'website.delete_page').then(function (val, field, $dialog) {

                if ($dialog.find('input[type="checkbox"]').is(':checked')) {
                    ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                        model: 'website',
                        method: 'delete_page',
                        args: [self.mo_id],
                        kwargs: {
                            context: context
                        },
                    }).then(function () {
                        if(typeof callback === 'function')
                            callback();
                        else
                            window.location = "/?spm=1";
                    });
                }
            });
        });
    },
    add_menu: function () {
        var self = this;
        var dialog = new MenuEntryDialog(this, {menu_link_options: false}, undefined, {});
        dialog.on('save', this, function (link) {
            var new_menu = {
                id: _.uniqueId('new-'),
                name: link.text,
                url: link.url,
                new_window: link.isNewWindow,
                parent_id: false,
                sequence: 0,
                children: [],
            };
            self.flat[new_menu.id] = new_menu;
            self.$('.oe_menu_editor').append(
                qweb.render('website.pagesMenu.submenu', { submenu: new_menu }));
        });
        dialog.open();
    },
});

website.TopBar.include({
    start: function () {
        this.content_menu = new TopBarContent();
        var def = this.content_menu.attachTo($('.oe_content_menu'));
        return $.when(this._super(), def);
    }
});

/*var SelectEditMenuDialog = widget.Dialog.extend({
    template: 'website.contentMenu.dialog.select',
    init: function (parent, options) {
        var self = this;
        self.roots = [{id: null, name: _t("Top Menu")}];
        $("[data-content_menu_id]").each(function () {
            self.roots.push({id: $(this).data("content_menu_id"), name: $(this).attr("name")});
        });
        this._super(parent, _.extend({}, {
            title: _t("Select a Menu"),
            save_text: _t("Continue")
        }, options || {}));
    },
    save: function () {
        this.final_data = parseInt(this.$el.find("select").val() || null);
        this._super.apply(this, arguments);
    }
});


/*var EditMenuDialog = widget.Dialog.extend({
    template: 'website.contentMenu.dialog.edit',
    events: _.extend({}, widget.Dialog.prototype.events, {
        'click a.js_add_menu': 'add_menu',
        'click button.js_edit_menu': 'edit_menu',
        'click button.js_delete_menu': 'delete_menu',
    }),
    init: function (parent, options, menu) {
        this.menu = menu;
        this.root_menu_id = menu.id;
        this.flat = this.flatenize(menu);
        this.to_delete = [];
        this._super(parent, _.extend({}, {
            title: _t("Edit Menu"),
            size: 'medium',
        }, options || {}));
    },
    start: function () {
        var r = this._super.apply(this, arguments);
        this.$('.oe_menu_editor').nestedSortable({
            listType: 'ul',
            handle: 'div',
            items: 'li',
            maxLevels: 2,
            toleranceElement: '> div',
            forcePlaceholderSize: true,
            opacity: 0.6,
            placeholder: 'oe_menu_placeholder',
            tolerance: 'pointer',
            attribute: 'data-menu-id',
            expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
        });
        return r;
    },
    flatenize: function (node, dict) {
        dict = dict || {};
        var self = this;
        dict[node.id] = node;
        node.children.forEach(function (child) {
            self.flatenize(child, dict);
        });
        return dict;
    },
    add_menu: function () {
        var self = this;
        var dialog = new MenuEntryDialog(this, {menu_link_options: true}, undefined, {});
        dialog.on('save', this, function (link) {
            var new_menu = {
                id: _.uniqueId('new-'),
                name: link.text,
                url: link.url,
                new_window: link.isNewWindow,
                parent_id: false,
                sequence: 0,
                children: [],
            };
            self.flat[new_menu.id] = new_menu;
            self.$('.oe_menu_editor').append(
                qweb.render('website.pagesMenu.submenu', { submenu: new_menu }));
        });
        dialog.open();
    },
    edit_menu: function (ev) {
        var self = this;
        var menu_id = $(ev.currentTarget).closest('[data-menu-id]').data('menu-id');
        var menu = self.flat[menu_id];
        if (menu) {
            var dialog = new MenuEntryDialog(this, {}, undefined, menu);
            dialog.on('save', this, function (link) {
                var id = link.id;
                var menu_obj = self.flat[id];
                _.extend(menu_obj, {
                    'name': link.text,
                    'url': link.url,
                    'new_window': link.isNewWindow,
                });
                var $menu = self.$('[data-menu-id="' + id + '"]');
                $menu.find('.js_menu_label').first().text(menu_obj.name);
            });
            dialog.open();
        } else {
            alert("Could not find menu entry");
        }
    },
    delete_menu: function (ev) {
        var $menu = $(ev.currentTarget).closest('[data-menu-id]');
        var mid = $menu.data('menu-id')|0;
        if (mid) {
            this.to_delete.push(mid);
        }
        $menu.remove();
    },
    save: function () {
        var _super = this._super.bind(this);
        var self = this;
        var new_menu = this.$('.oe_menu_editor').nestedSortable('toArray', {startDepthCount: 0});
        var levels = [];
        var data = [];
        var context = base.get_context();
        // Resequence, re-tree and remove useless data
        new_menu.forEach(function (menu) {
            if (menu.id) {
                levels[menu.depth] = (levels[menu.depth] || 0) + 1;
                var mobj = self.flat[menu.id];
                mobj.sequence = levels[menu.depth];
                mobj.parent_id = (menu.parent_id|0) || menu.parent_id || self.root_menu_id;
                delete(mobj.children);
                data.push(mobj);
            }
        });
        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'website.menu',
            method: 'save',
            args: [[context.website_id], { data: data, to_delete: self.to_delete }],
            kwargs: {
                context: context
            },
        }).then(function () {
            return _super();
        });
    },
});*/

var MenuEntryDialog = widget.LinkDialog.extend({
    init: function (parent, options, editor, data) {
        data.text = data.name || '';
        data.isNewWindow = data.new_window;
        this.data = data;
        this.menu_link_options = options.menu_link_options;
        return this._super.apply(this, arguments);
    },
    start: function () {
        var self = this;
        this.$(".o_link_dialog_preview").remove();
        this.$(".window-new, .link-style").closest(".form-group").remove();
        this.$("label[for='o_link_dialog_label_input']").text(_t("Menu Label"));
        /*if (this.menu_link_options) { // add menu link option only when adding new menu
            //this.$('#o_link_dialog_label_input').closest('.form-group').after(qweb.render('website.contentMenu.dialog.edit.link_menu_options'));
            this.$('input[name=link_menu_options]').on('change', function() {
                self.$('#o_link_dialog_url_input').closest('.form-group').toggle();
            });
        }*/
        this.$modal.find('.modal-lg').removeClass('modal-lg')
                   .find('.col-md-8').removeClass('col-md-8').addClass('col-xs-12');

        return this._super.apply(this, arguments);
    },
    save: function () {
        var context = base.get_context();
        var label = this.$('#o_link_dialog_label_input');
        if (!label.val() || !label[0].checkValidity()) {
            label.closest('.form-group').addClass('has-error');
            label.focus();
            return;
        }
        var url = this.$('#o_link_dialog_url_input');
        if (!url.val() || !url[0].checkValidity()) {
            url.closest('.form-group').addClass('has-error');
            url.focus();
            return;
        }
        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'website',
            method: 'new_link',
            args: [label.val(),url.val() ],
            kwargs: {
                context: context
            },
        }).then(function () {
            //Redraw menu
            editor.reload();
        });
        
        
        /*if (this.$('input[name=link_menu_options]:checked').val() === 'new_page') {
            window.location = '/website/add/' + encodeURIComponent($e.val()) + '?add_menu=1';
            return;
        }*/
        return this._super.apply(this, arguments);
    }
});

return {
    'TopBar': TopBarContent,
};

});
