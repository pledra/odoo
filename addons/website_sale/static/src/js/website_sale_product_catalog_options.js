odoo.define('website_sale.product_catalog_options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');
var rpc = require('web.rpc');

var _t = core._t;
var QWeb = core.qweb;

options.registry.product_catalog = options.Class.extend({
	gridSize: function(previewMode, value, $li) {
		if (previewMode === 'reset') {
			return;
		}
		var self = this;
        this.$el.on('mouseenter', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).addClass('oe_hover');
        });
        this.$el.on('mouseleave', 'ul[name="size"] table', function (event) {
            $(event.currentTarget).removeClass('oe_hover');
        });
        this.$el.on('mouseover', 'ul[name="size"] td', function (event) {
            var $td = $(event.currentTarget);
            var $table = $td.closest('table');
            var x = $td.index() + 1;
            var y = $td.parent().index() + 1;

	        var tr = [];
	        for (var yi = 0; yi < y; yi++) {
	            tr.push('tr:eq(' + yi + ')');
	        }
	        var $select_tr = $table.find(tr.join(','));
	        var td = [];
	        for (var xi = 0; xi < x; xi++) {
	            td.push('td:eq(' + xi + ')');
	        }
	        var $select_td = $select_tr.find(td.join(','));
	        $table.find('td').removeClass('select');
	        $select_td.addClass('select');
      });
	}
});
});