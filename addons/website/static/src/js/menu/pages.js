odoo.define('website.editPages', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var weContext = require('web_editor.context');
var editor = require('web_editor.editor');
var websiteNavbarData = require('website.navbar');
var widget = require('web_editor.widget');
var websiteNewMenu = require('website.newMenu');
var websiteSeo = require('website.seo');


var qweb = core.qweb;
var _t = core._t;

var PageMenuEntryDialog = widget.LinkDialog.extend({
    xmlDependencies: widget.LinkDialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.contentMenu.xml']
    ),
  
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
        var context = weContext.get();
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
        this._rpc({
            model: 'website',
            method: 'new_link',
            args: [label.val(),url.val() ],
            kwargs: {
                context: context
            },
        }).then(function () {
            //Redraw menu
            window.location.reload(true);
        });

        return this._super.apply(this, arguments);
    }
});

var ManagePagesMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    xmlDependencies: ['/website/static/src/xml/website.contentMenu.xml', '/website/static/src/xml/website.xml'],
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions, {
        open_management_page_menu: '_openManagementPageMenu',
        save_management_page_menu: '_saveManagementPageMenu',
        load_page_info: '_loadPageInfo',
        close_page_info: '_closePageInfo',
        save_page_info: '_savePageInfo',
        new_menu: '_newMenu',
        new_page: '_newPage',
        clone_page: '_clonePage',
        delete_page: '_deletePage',
        go_to_seo: '_goToSeo',
        go_to_track: '_goToTrack',
    }),
    /**
     * Load pages and initialize drag & drop feature
     *
     * @override
     */
    start: function () {
        if (location.search.indexOf("show_seo") > -1){
            this.websiteSeoConfig = new websiteSeo.SeoConfigurator();
            this.websiteSeoConfig.open();
        }
        
        var self = this;
        self.to_delete = [];
        self.websiteSeoConfig = null;
        self._loadPageManagementMenu().then(function(e){
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
                self._openManagementPageMenu();
        });
    },
    _loadPageManagementMenu: function () {
        var self = this;
        var context = weContext.get();
        return self._rpc({
            model: 'website.page',
            method: 'get_pages',
            args: [context.website_id],
            kwargs: {
                context: context
            },
        }).then(function (result) {
            return self._rpc({
                model: 'website.page',
                method: 'get_tree',
                args: [context.website_id],
                kwargs: {
                    context: context
                },
            }).then(function (menu) {
                self.menus = menu;
                self.root_menu_id = menu.id;
                self.flat = self._flatenize(menu);
                self.flat = self._flatenize(result.pages, self.flat);
                $(qweb.render('website.pagesMenu', {pages: result.pages, tree_menu:menu, page_url: window.location.pathname})).appendTo(".oe_page_management_menu");
            });
        });
    },
    _openManagementPageMenu: function() {
        this.$el.toggleClass('open');
    },
    _flatenize: function (nodes, dict) {
        dict = dict || {};
        var self = this;
        nodes.forEach(function(node){
            dict[node.id] = node;
            if(typeof node.children === 'undefined')
                node.children = [];
            node.children.forEach(function (child) {
                self._flatenize([child], dict);
            });
        });
        
        return dict;
    },
    _saveManagementPageMenu: function(){
        var self = this;
        var new_menu = this.$('#pages_management_menu_pages').nestedSortable('toArray', {startDepthCount: 0});
        var levels = [];
        var data = [];
        var context = weContext.get();
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
        
        self._rpc({
            model: 'website.page',
            method: 'save_tree_menu',
            args: [[context.website_id], { data: data, to_delete: self.to_delete }],
            kwargs: {
                context: context
            },
        }).then(function () {
            //Redraw menu
            window.location.reload(true);
        });
        
    },
    _loadPageInfo: function(data){        
        var self = this;
        var context = weContext.get();
        return this._rpc({
            model: 'website.page',
            method: 'get_page_from_path',
            args: [data.pagePath,context.website_id],
            kwargs: {
                context: context
            },
        }).then(function (page) {
            $(".oe_page_management_page_info").html($(qweb.render('website.pagesMenu.page_info', {page: page[0], server_url:window.location.origin})));
            //TODO: SEO
            //self.websiteSeoConfig = new websiteSeo.Configurator(self, {page: page[0],model: data.model});
            //self.websiteSeoConfig.appendTo($('#seo_promote'));
            $(".oe_page_management_page_info").show();
            $("button[data-action='save_management_page_menu']").prop('disabled', true);
        });
    },
    _closePageInfo: function(){
        $(".oe_page_management_page_info").hide();
        $("button[data-action='save_management_page_menu']").prop('disabled', false);
    },
    _savePageInfo: function(data){
        var self = this;
        var context = weContext.get();
        var page_name = $(".oe_page_management_page_info #page_name").val();
        var page_path = $(".oe_page_management_page_info #page_path").val();
        var is_menu = $(".oe_page_management_page_info #is_menu").prop('checked');
        var is_homepage = $(".oe_page_management_page_info #is_homepage").prop('checked');
        //var website_meta_title = $(".oe_page_management_page_info input[name=seo_page_title]").val();
        //var website_meta_description = $('.oe_page_management_page_info textarea[name=seo_page_description]').val();
        var params = {
            name: page_name, 
            path: page_path,
            is_menu: is_menu,
            is_homepage: is_homepage,
            id: data.id,
            //website_meta_title: website_meta_title,
            //website_meta_description: website_meta_description,
        };
        //ES6: Object.assign(seo_fields, this.websiteSeoConfig.get_fields());
        //var seo_fields = this.websiteSeoConfig.get_fields();
        //for (var attrname in seo_fields) { params[attrname] = seo_fields[attrname]; }
        self._rpc({
            model: 'website.page',
            method: 'save_page_info',
            args: [[context.website_id], params],
            kwargs: {
                context: context
            },
        }).then(function () {
            //Redirect to the modified page
            window.location = page_path + '?spm=1';
            //Just some not very usefull ui but help user to see it is working
            $(".oe_page_management_page_info").hide();
            $("button[data-action='save_management_page_menu']").prop('disabled', false);
        });
    },
    _newMenu: function() {
        var self = this;
        var dialog = new PageMenuEntryDialog(this, {menu_link_options: false}, undefined, {});
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
    _newPage: function() {
        $('#new-content-menu').click();
    },
    _clonePage: function(data){
        var self = this;
        var context = weContext.get();
        self.mo_id = data.id;
        self._rpc({
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
    _deletePage: function (data) {
        var self = this;
        var context = weContext.get();
        var moID = data.id;
        
        var def = $.Deferred();
        
        // Search the page dependencies
        this._getPageDependencies(moID, context)
        .then(function (dependencies) {
        // Inform the user about those dependencies and ask him confirmation
            var confirmDef = $.Deferred();
            Dialog.safeConfirm(self, "", {
                title: _t("Delete Page"),
                $content: $(qweb.render('website.delete_page', {dependencies: dependencies})),
                confirm_callback: confirmDef.resolve.bind(confirmDef),
                cancel_callback: def.resolve.bind(self),
            });
            return confirmDef;
        }).then(function () {
        // Delete the page if the user confirmed
            return self._rpc({
                model: 'website',
                method: 'delete_page',
                args: [moID],
                context: context,
            });
        }).then(function () {
        // Redirect to homepage as the page is now deleted
            window.location.href = "/?spm=1";
        }, def.reject.bind(def));
    },
    _goToSeo: function(data) {
        window.location.href = data.path + "?show_seo=1";
    },
    _goToTrack: function(data) {
        alert("todo");
    },
    /**
     * Retrieves the page dependencies for the given object id.
     *
     * @private
     * @param {integer} moID
     * @param {Object} context
     * @returns {Deferred<Array>}
     */
    _getPageDependencies: function (moID, context) {
        return this._rpc({
            model: 'website',
            method: 'page_search_dependencies',
            args: [moID],
            context: context,
        });
    },
    _getMainObject: function () {
        var repr = $('html').data('main-object');
        var m = repr.match(/(.+)\((\d+),(.*)\)/);
        return {
            model: m[1],
            id: m[2] | 0,
        };
    },
});

websiteNavbarData.websiteNavbarRegistry.add(ManagePagesMenu, '#manage-pages-menu');

return {
    ManagePagesMenu: ManagePagesMenu,
    PageMenuEntryDialog: PageMenuEntryDialog,
};

});
