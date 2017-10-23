odoo.define('website_sale.product_catalog', function (require) {
'use strict';

var ajax = require('web.ajax');
var base = require('web_editor.base');
var core = require('web.core');
var rpc = require('web.rpc');
var website = require('website.website');
var Widget = require('web.Widget');
var utils = require('web.utils');

var QWeb = core.qweb;
var ProductCatalog = Widget.extend({
	template: 'website_sale.product_catalog',
	xmlDependencies: ['/website_sale/static/src/xml/website_sale_product_catalog.xml'],
    /**
     * Initialize all options which are need to render widget.
     * @constructor
     * @override
     * @param {jQuery} $target
     */
    init: function ($target) {
		this._super.apply(this, arguments);
		this.$target = $target;
		this.catalogType = this.$target.attr('data-catalog-type');
		this.size = 12/this.$target.attr('data-x');
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Fetch product details.
     *
     * @override
     * @returns {Deferred}
     */
    willStart: function () {
        var self = this;
        var def = rpc.query({
            route: '/get_product_catalog_details',
            params: {
                'domain': this._getDomain(),
                'sortby': this._getSortby(),
                'limit': this._getLimit(),
            }
        }).then(function (result) {
            self.products = result.products;
        });
        return $.when(this._super.apply(this, arguments), def);
    },
    _getDomain: function () {
        var domain;
        var selection = this.$target.attr('data-product-selection');
        switch (selection) {
            case 'all':
                domain = [];
                break;
            case 'category':
                domain = ['public_categ_ids', 'child_of', [parseInt(this.$target.attr('data-catagory-id'))]];
                break;
            case 'manual':
                var productIds = this.$target.attr('data-productIds').split(',').map(Number);
                domain = ['id', 'in', productIds]
                break;
        }
		return domain;
    },
    _getSortby: function () {
		var sortby = this.$target.attr('data-sortby');
		return sortby;
    },
    _getLimit: function () {
		var limit;
		if (this.catalogType === 'grid') {
			limit = this.$target.attr('data-x') * this.$target.attr('data-y');
		} else {
			limit = this.$target.attr('data-carousel');
		}
		return limit;
    },
    /**
     * Get product ids.
     *
     * @private
     * @returns {Array} Contains product ids.
     */
    _getProductIds: function () {
        return _.map(this.$target.find('.product-item'), function(el) {
            return $(el).data('product-id');
        });
    },

});
base.ready().then(function () {
    if ($('.s_product_catalog').length) {
		$('.s_product_catalog').each(function () {
			var productCatalog = new ProductCatalog($(this));
			$(this).find('.product_grid').remove();
			productCatalog.appendTo($(this).find('.container'));
		});
    }
});
return {
    ProductCatalog: ProductCatalog
};
});
