odoo.define('website_sale.product_catalog_options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');
var rpc = require('web.rpc');

var _t = core._t;
var QWeb = core.qweb;

options.registry.product_catalog = options.Class.extend({
	start: function() {
		this._super.apply(this, arguments);
		if (this.$target.data('catalog-type') === 'grid') {
	        this._setGrid();
	        this._bindGridEvents();
		}
		this.$el.find('[data-carousel]:first').parent().parent().toggle(this.$target.data('catalog-type') === 'carousel');
		this.$el.find('[data-grid]:first').parent().parent().toggle(this.$target.data('catalog-type') === 'grid');
	},
	_setGrid: function() {
		var x = this.$target.data('x');
        var y = this.$target.data('y');
        var $grid = this.$el.find('ul[name="size"]');
        var $selected = $grid.find('tr:eq(0) td:lt(' + x + ')');
        if (y >= 2) {
            $selected = $selected.add($grid.find('tr:eq(1) td:lt(' + x + ')'));
        }
        if (y >= 3) {
            $selected = $selected.add($grid.find('tr:eq(2) td:lt(' + x + ')'));
        }
        if (y >= 4) {
            $selected = $selected.add($grid.find('tr:eq(3) td:lt(' + x + ')'));
        }
        $selected.addClass('selected');
	},
	grid: function (previewMode, value, $li) {
		if (!this.__click) {
            return;
        }
        var self = this;
        var $td = this.$el.find('.select:last');
        if ($td.length) {
            var x = $td.index() + 1;
            var y = $td.parent().index() + 1;
            this.$target.attr('data-x', x);
            this.$target.attr('data-y', y);
        }
	},
	_bindGridEvents: function () {
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
    },
	catalogType: function (previewMode, value, $li) {
        if (!this.__click && previewMode == 'reset') {
            return;
        }
        this.$target.attr('data-catalog-type', value);
        var self = this;
        var $td = this.$el.find('.select:last');
        if ($td.length) {
            var x = $td.index() + 1;
            var y = $td.parent().index() + 1;
            this.$target.attr('data-x', x);
            this.$target.attr('data-y', y);
        }
        this.$el.find('[data-carousel]:first').parent().parent().toggle(value === 'carousel');
        this.$el.find('[data-grid]:first').parent().parent().toggle(value === 'grid');
    },
});
});