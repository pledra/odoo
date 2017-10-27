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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * formating currency for the website sale display
     *
     * @private
     * @param {float|false} value that should be formatted.
     * @param {string} currency symbol.
     * @param {string} position should be either before or after.
     * @param {integer} the number of digits that should be used,
     *   instead of the default digits precision in the field.
     * @returns {string} Returns a string representing a float and currency symbol.
     */
    _formatCurrencyValue: function (value, currency_symbol, position, currency_decimal_places) {
        var l10n = core._t.database.parameters;
        value = _.str.sprintf('%.' + currency_decimal_places + 'f', value || 0).split('.');
        value[0] = utils.insert_thousand_seps(value[0]);
        value = value.join(l10n.decimal_point);
        if (position === "after") {
            value += currency_symbol;
        } else {
            value = currency_symbol + value;
        }
        return value;
    },

    /**
     * formating description for the website sale display
     *
     * @private
     * @param {string} get description.
     * @returns {string} Contains string with replace '\n' to '<br>'.
     */
    _formatDescriptionValue: function (description_sale) {
        return description_sale.split("\n").join("<br>");
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
