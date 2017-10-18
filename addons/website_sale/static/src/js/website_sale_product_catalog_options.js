odoo.define('website_sale.product_catalog_options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');
var productCatalog = require('website_sale.product_catalog');
var rpc = require('web.rpc');

var _t = core._t;
var QWeb = core.qweb;

options.registry.product_catalog = options.Class.extend({
    start: function () {
        this._super.apply(this, arguments);
        if (this.$target.data('catalog-type') === 'grid') {
            this._setGrid();
            this._bindGridEvents();
        }
        this.$el.find('[data-catalog-type='+this.$target.data('catalog-type')+']').addClass('active');
        this.$el.find('[data-product-selection='+this.$target.data('product-selection')+']').addClass('active');
        this.$el.find('[data-shortby='+this.$target.data('shortby')+']').addClass('active');
        this.$el.find('[data-carousel]:first').parent().parent().toggle(this.$target.data('catalog-type') === 'carousel');
        this.$el.find('[data-grid]:first').parent().parent().toggle(this.$target.data('catalog-type') === 'grid');
    },
    _setGrid: function () {
        var $td = this.$el.find('.select:last');
        if ($td.length) {
            this.$target.attr('data-x', $td.index() + 1);
            this.$target.attr('data-y', $td.parent().index() + 1);
        }
        var x = this.$target.attr('data-x');
        var y = this.$target.attr('data-y');
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
        $grid.find('td').removeClass('selected');
        $selected.addClass('selected');
    },
    grid: function (previewMode, value, $li) {
        if (!this.__click || previewMode == 'reset') return;
        this._setGrid();
        this._renderProducts();
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Bind events of grid option.
     *
     * @private
     */
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
    _renderProducts: function () {
        this.productCatalog = new productCatalog.ProductCatalog(this.$target);
        this.$target.find('.product_grid').remove();
        this.productCatalog.appendTo(this.$target.find('.container'));
    },
	catalogType: function (previewMode, value, $li) {
        if (!this.__click || previewMode == 'reset') return;

        this.$target.attr('data-catalog-type', value);
        this.$el.find('[data-catalog-type]').removeClass('active');
        $li.toggleClass('active',this.$target.attr('data-catalog-type') === value);
        this.$el.find('[data-carousel]:first').parent().parent().toggle(value === 'carousel');
        this.$el.find('[data-grid]:first').parent().parent().toggle(value === 'grid');
        this._setGrid();
    },
    productSelection: function (previewMode, value, $li) {
        if (!this.__click || previewMode == 'reset') return;
        this.$target.attr('data-product-selection', value);
        this.$el.find('[data-product-selection]').removeClass('active');
        $li.toggleClass('active',this.$target.attr('data-product-selection') === value);
        switch (value) {
            case 'all':
                this.$target.attr('data-product-domain', []);
                break;
            case 'category':
                this.categorySelection();
                break;
            case 'manual':
                this.manualSelection();
                break;
            }

    },
    categorySelection: function () {
        var self = this;
        rpc.query({
            model: 'product.public.category',
            method: 'search_read',
            fields: ['id', 'name'],
        }).then(function (result) {
            var dialog = new Dialog(null, {
                title: _t('Select Product Category'),
                $content: $(QWeb.render('product_catalog.catagorySelection')),
                buttons: [
                    {text: _t('Save'), classes: 'btn-primary', close: true, click: function () {
                        var categoryID = dialog.$content.find('[name="selection"]').val();
                        self.$target.attr('data-catagory-id', categoryID);

                        self.productCatalog.options.domain = ['public_categ_ids', '=', parseInt(categoryID)];
                        self._renderProductCatalog().then(function () {
                            self.$target.attr('data-reorder-ids', self.productCatalog._getProductIds().join(','));
                        });
                    }},
                    {text: _t('Discard'), close: true}
                ]
            }).open();
        });
    },
    manualSelection: function () {
    },
    sortby: function (previewMode, value, $li) {
        if (!this.__click || previewMode == 'reset') return;
        this.$target.attr('data-sortby', value);
        this.$el.find('[data-sortby]').removeClass('active');
        $li.toggleClass('active',this.$target.attr('data-sortby') === value);
        this._renderProducts();
    }
});
});
