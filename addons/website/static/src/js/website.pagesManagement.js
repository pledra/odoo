odoo.define('website.pagesManagement', function (require) {
"use strict";

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var editor = require('web_editor.editor');
var widget = require('web_editor.widget');
var website = require('website.website');
var contentMenu = require('website.contentMenu');
var websiteSeo = require('website.seo');

var _t = core._t;
var qweb = core.qweb;

$(document).on('click', '.js_pages_management .js_delete_page', function (e) {
    var topBar = new contentMenu.TopBar();
    topBar.delete_page(getMainObject(this).id, function(){location.reload();});
});
$(document).on('click', '.js_pages_management .js_rename_page', function (e) {
    var topBar = new contentMenu.TopBar();
    topBar.rename_page(getMainObject(this).id, function(){location.reload();});
});

var getMainObject = function (self) {
    var repr = $(self).closest(".pages_management_main_object").data('main-object');
    var m = repr.match(/(.+)\((\d+),(.*)\)/);
    if (!m) {
        return null;
    } else {
        return {
            model: m[1],
            id: m[2]|0
        };
    }
};
/*
ajax.loadXML('/website/static/src/xml/website.pagesManagement.xml', qweb);

var TopBarContent = Widget.extend({
    start: function () {
        var self = this;
        return this._super();
    },
    manage_pages: function (action_before_reload) {
        var context = base.get_context();
        var def = $.Deferred();
        def.resolve(null);
        
        return def.then(function (root_id) {
            return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'website.page',
                method: 'get_pages',
                args: [context.website_id],
                kwargs: {
                    context: context
                },
            }).then(function (pages) {
                var dialog = new EditMenuDialog(this, {}, pages).open();
                dialog.on("save", null, function () {
                    $.when(action_before_reload && action_before_reload()).then(function () {
                        editor.reload();
                    });
                });
                return dialog;
            });
        });
    }
});


website.TopBar.include({
    start: function () {
        this.content_menu = new TopBarContent();
        var def = this.content_menu.attachTo($('.oe_pages_menu'));
        return $.when(this._super(), def);
    }
});

var EditMenuDialog = widget.Dialog.extend({
    template: 'website.pagesManagement.dialog.edit',
    events: _.extend({}, widget.Dialog.prototype.events, {
        'click a.js_goto_page': 'goto_page',
        'click button.js_publish_page': 'publish_page',
        'click button.js_edit_page': 'edit_page',
        'click button.js_delete_page': 'delete_page',
        'click button.js_rename_page': 'rename_page',
        'click a.js_create_page': 'create_page',
    }),
    init: function (parent, options, pages) {
        this.pages = pages;
        this._super(parent, _.extend({}, {
            title: _t("Pages Management"),
            size: 'medium',
        }, options || {}));
    },
    delete_page: function(ev){
      var topBar = new contentMenu.TopBar();
      topBar.delete_page();
    },
    rename_page: function(ev){
      var topBar = new contentMenu.TopBar();
      topBar.rename_page();
    },
    publish_page: function (ev){
        var page_id = $(ev.currentTarget).closest('[data-page-id]').data('page-id');
        ajax.jsonRpc('/website/publish', 'call', {'id': +page_id, 'object': 'website.page'})
            .then(function (result) {
                $(ev.currentTarget).closest('.js_publish_page').toggleClass("fa-eye-slash fa-eye").toggleClass("btn-primary btn-danger");
            }).fail(function (err, data) {
                website.error(data.data ? data.data.arguments[0] : "", data.data ? data.data.arguments[1] : data.statusText, '/web#return_label=Website&model=website.page&id='+page_id);
            });
    },
    edit_page: function (ev) {
        var page_path = $(ev.currentTarget).closest('[data-page-path]').data('page-path');
        document.location = page_path + '?enable_editor=1';
    },
    goto_page: function (ev) {
        var self = this;
        var page_path = $(ev.currentTarget).closest('[data-page-path]').data('page-path');
        document.location = page_path;
    },
    create_page: function (ev) {
        var topBar = new contentMenu.TopBar();
        topBar.new_page();
    }
});


return {
    'TopBar': TopBarContent,
    'EditMenuDialog': EditMenuDialog,
};*/

});
