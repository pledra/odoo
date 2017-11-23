odoo.define('account_portal_invoices.account_portal_invoices', function (require) {
'use strict';

require('web.dom_ready');
var ajax = require('web.ajax');
var config = require('web.config');
var Widget = require('web.Widget');

if(!$('.o_account_portal_invoices').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_account_portal_invoices'");
}

if($(".o_portal_invoice").length){
    var href = $(location).attr("href"),
        invoice_id = href.match(/invoice\/([0-9]+)/),
        access_token = href.match(/invoice\/([^\/?]*)/),
        params = {};
    
    params.token = access_token ? access_token[1] : '';
    params.invoice_id = invoice_id ? invoice_id[1]: '';
    ajax.jsonRpc('/my/invoice/pdf/', 'call', params).then(function (data) {
        var $iframe = $('iframe#o_portal_account_actions')[0];
        $iframe.contentWindow.document.open('text/pdfreplace');
        $iframe.contentWindow.document.write(data);
});
var $bs_sidebar = $(".o_account_portal_invoices .bs-sidebar");
    $(window).on('resize', _.throttle(adapt_sidebar_position, 200, {leading: false}));
    adapt_sidebar_position();

    function adapt_sidebar_position() {
        $bs_sidebar.css({
            position: "relative",
            width: "",
        });
        if (config.device.size_class >= config.device.SIZES.MD) {
            $bs_sidebar.css({
                position: "fixed",
                width: $bs_sidebar.outerWidth(),
            });
        }
    }

    $bs_sidebar.affix({
        offset: {
            top: 0,
            bottom: $('body').height() - $('#wrapwrap').outerHeight() + $("footer").outerHeight(),
        },
    });
});