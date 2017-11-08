odoo.define('website_sale_comparison.product_catalog', function (require) {
'use strict';

require('web.dom_ready');
var ProductCatalog = require('website_sale.product_catalog');
var ProductComparison = require('website_sale_comparison.comparison');
var WebsiteSaleUtils = require('website_sale.utils');

if (!$('.s_product_catalog').length) {
    return $.Deferred().reject("DOM doesn't contain '.s_product_catalog'");
}

ProductCatalog.ProductCatalog.include({
    xmlDependencies: ProductCatalog.ProductCatalog.prototype.xmlDependencies.concat(
        ['/website_sale_comparison/static/src/xml/website_sale_comparison_product_catalog.xml']
    ),
    events: _.extend({}, ProductCatalog.ProductCatalog.prototype.events, {
        'click .add_to_compare': '_onClickAddToCompare',
    }),
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function(){
            self.Comparison = new ProductComparison.ProductComparison();
            self.Comparison.appendTo('body');
        });
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add product into compare list.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClickAddToCompare: function (event) {
        var variantID = $(event.currentTarget).data('product-variant-id');
        if (this.Comparison.comparelist_product_ids.length < this.Comparison.product_compare_limit) {
            this.Comparison.add_new_products(variantID);
            WebsiteSaleUtils.animate_clone($('#comparelist .o_product_panel_header'), $(event.currentTarget).parents('[class^="col-"]'), -50, 10);
        } else {
            this.Comparison.$el.find('.o_comparelist_limit_warning').show();
            this.Comparison.show_panel(true);
        }
    },
});


});
