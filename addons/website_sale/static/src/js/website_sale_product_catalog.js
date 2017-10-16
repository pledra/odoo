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
		this.sizes = {4: 3, 3: 4, 2: 6, 1: 12};
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
		var domain = [];
		var selection = this.$target.data('product-selection');
		return domain;
    },
    _getSortby: function () {
		var sortby = this.$target.data('sortby');
		return sortby;
    },
    _getLimit: function () {
		var catalogType = this.$target.data('catalog-type');
		var limit;
		if (catalogType === 'grid') {
			limit = this.$target.data('x') * this.$target.data('y');
		} else {
			limit = this.$target.data('carousel');
		}
		return limit;
    }

});
base.ready().then(function () {
    if ($('.s_product_catalog').length) {
		$('.s_product_catalog').each(function () {
			var productCatalog = new ProductCatalog($(this));
			productCatalog.appendTo($(this).find('.container'));
		});
    }
});
});