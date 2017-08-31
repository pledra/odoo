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

        //return this._super.apply(this, arguments);
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
        new_item: '_newItem',
        new_page: '_newPage',
        clone_page: '_clonePage',
        delete_object: '_deleteObject',
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
                attribute: 'data-object-id',
                expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
                connectWith: '#pages_management_other_pages',
                stop: function(event, ui) { 
                    self._truncatePageName(ui.item);
                },
                receive: function(event, ui) { 
                    $("[data-action='save_management_page_menu']").show();
                    var id = $(ui.item).data('object-id');
                    if (id.indexOf('menu') !== -1){
                        var index = self.to_delete.indexOf(id);
                        if(index !== -1)
                            self.to_delete.splice(index, 1);
                    }
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
                attribute: 'data-object-id',
                expression: '()(.+)', // nestedSortable takes the second match of an expression (*sigh*)
                connectWith: '#pages_management_menu_pages',
                stop: function(event, ui) { 
                    self._truncatePageName(ui.item);
                },
                receive: function(event, ui) { 
                    $("[data-action='save_management_page_menu']").show();
                    var id = $(ui.item).data('object-id');
                    if (id.indexOf('menu') !== -1)
                        self.to_delete.push(id);
                },
            });
            
            // We can't truncate too long page name with css (table, float..) and can't do it 
            // by limiting the length of the string (every character hasnt the same width (i vs m))
            // plus we have 2 level nested list.
            // So we will set the allowed space to exactly what we have
          
            
            
            if (location.search.indexOf("spm") > -1){
                self._openManagementPageMenu();
                $(".oe_page_management_menu .current_page").click();
            }
            $("[data-action='save_management_page_menu']").hide();
        });
    },
    _truncatePageName: function(items){ 
        items.each(function(index){
            var available_width = $('.form-control', this).width() - 38 + 'px';
            $(".js_menu_label", this).css({
                'width': available_width,
                'overflow': 'hidden',
                'display': 'inline-block',
                'text-overflow': 'ellipsis',
                'white-space': 'nowrap'
            });
        });
    },
    _loadPageManagementMenu: function () {
        var self = this;
        var context = weContext.get();
        return self._rpc({
            //TODO: This call should be remove but I don't know how to get the website.homepage_id
            model: 'website',
            method: 'get_homepage',
            args: [context.website_id],
            kwargs: {
                context: context
            },
        }).then(function (homepage_path) {
            return self._rpc({
                model: 'website.page',
                method: 'get_pages_not_in_menu',
                args: [context.website_id],
                kwargs: {
                    context: context
                },
            }).then(function (result) {
                return self._rpc({
                    model: 'website.menu',
                    method: 'get_tree',
                    args: [context.website_id],
                    kwargs: {
                        context: context
                    },
                }).then(function (menu) {
                    //We don't need the root_menu in the page management UI
                    menu = menu.children;
                    self.menus = menu;
                    self.root_menu_id = menu.id;
                    self.flat = self._flatenize(menu);
                    self.flat = self._flatenize(result.pages, self.flat);
                    $(qweb.render('website.pagesMenu', {pages: result.pages, tree_menu:menu, homepage_path: homepage_path, current_page_url: window.location.pathname})).appendTo(".oe_page_management_menu");
                });
            });
        });
    },
    _openManagementPageMenu: function() {
        this.$el.toggleClass('open');
        this._truncatePageName($(".oe_page_management_menu li[data-object-id]"));
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
            model: 'website.menu',
            method: 'save',
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
        return self._rpc({
            //TODO: This call should be remove but I don't know how to get the website.homepage_id
            model: 'website',
            method: 'get_homepage',
            args: [context.website_id],
            kwargs: {
                context: context
            },
        }).then(function (homepage_path) {
            return self._rpc({
                model: 'website.page',
                method: 'get_object',
                args: [data.objectId,context.website_id],
                kwargs: {
                    context: context
                },
            }).then(function (object) {
                var length_url = window.location.origin.length;
                var server_url = window.location.origin;
                var server_url_trunc = server_url;
                if(length_url > 30){
                    server_url_trunc = server_url.slice(0,14) + '..' + server_url.slice(length_url-14,length_url);
                }
                $(".oe_page_management_page_info").html($(qweb.render('website.pagesMenu.page_info', {page: object[0], homepage_path: homepage_path, server_url: window.location.origin, server_url_trunc: server_url_trunc, current_page_url: window.location.pathname})));
                $(".oe_page_management_page_info").show();
                $(".js_pagesMenu_btns .btn").prop('disabled', true);
            });
        });
    },
    _closePageInfo: function(){
        $(".oe_page_management_page_info").hide();
        $(".js_pagesMenu_btns .btn").prop('disabled', false);
    },
    _savePageInfo: function(data){
        var object_id = data.objectId.split("-")[1];
        var object_model = data.objectId.split("-")[0];
        
        var self = this;
        var context = weContext.get();
        
        var is_menu = $(".oe_page_management_page_info #is_menu").prop('checked');
        var object_name = $(".oe_page_management_page_info #object_name").val();
        var object_url = $(".oe_page_management_page_info #object_url").val();
        var params = {
            name: object_name, 
            url: object_url,
            is_menu: is_menu,
            id: data.objectId,
        };
        if(object_model == 'page'){
            params.is_homepage = $(".oe_page_management_page_info #is_homepage").prop('checked');
            params.website_published = $(".oe_page_management_page_info #is_published").prop('checked');
            //params.date_publish = $(".oe_page_management_page_info #date_publish").val();
        }
        self._rpc({
            model: 'website.page',
            method: 'save_page_info',
            args: [[context.website_id], params],
            kwargs: {
                context: context
            },
        }).then(function () {
            //If the saved element is a link, no point to redirect to its url, just reload the page (to redraw menu & page management)
            //TODO: To be discussed, should we redirect to url ? If the url point to a website's url its fine, but it is like google.com?
            window.location.href = object_model == 'page' ? object_url + '?spm=1' : "";
            //Just some not very usefull ui but help user to see it is working (redirect may take a few ms to execute)
            $(".oe_page_management_page_info").hide();
            $(".js_pagesMenu_btns .btn").prop('disabled', false);
        });
    },
    _newMenu: function() {
        var self = this;
        var dialog = new PageMenuEntryDialog(this, {menu_link_options: false}, undefined, {});
        
        dialog.open();
    },
    _newPage: function() {
        $('#new-content-menu').click();
    },
    _newItem: function() {
        //TODO: better way ?
        $('#o_new_content_menu_choices').toggleClass('o_hidden');
        this._openManagementPageMenu()
    },
    _clonePage: function(data){
        var self = this;
        var context = weContext.get();
        self._rpc({
            model: 'website.page',
            method: 'clone_object',
            args: [data.objectId],
            kwargs: {
                context: context,
            },
        }).then(function (path) {
            window.location.href = path;
        });
    },
    _deleteObject: function (data) {
        var self = this;
        var context = weContext.get();
        var moID = data.objectId;
        var object_model = moID.split("-")[0];
        var object_id = moID.split("-")[1];

        if(object_model == 'menu'){
            Dialog.safeConfirm(self, "", {
                title: _t("Delete Link"),
                $content: $(qweb.render('website.delete_link')),
                confirm_callback: function(){
                    self._rpc({
                        model: 'website',
                        method: 'delete_object',
                        args: [moID],
                        context: context,
                    }).then(function () {
                        window.location.href = "/?spm=1";
                    });
                },
                //cancel_callback: def.resolve.bind(self),
            });
        }
        else if(object_model == 'page'){
            var def = $.Deferred();
            // Search the page dependencies
            this._getPageDependencies(object_id, context)
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
                    method: 'delete_object',
                    args: [moID],
                    context: context,
                });
            }).then(function () {
            // Redirect to homepage as the page is now deleted
                window.location.href = "/?spm=1";
            }, def.reject.bind(def));
        }
        
    },
    _goToTrack: function(data) {
        window.location.href = '/r?u=' + encodeURIComponent(window.location.origin + data.path);
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
