odoo.define('payment_stripe.stripe', function(require) {
    "use strict";

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;
    var qweb = core.qweb;
    ajax.loadXML('/payment_stripe/static/src/xml/stripe_templates.xml', qweb);

    // The following currencies are integer only, see
    // https://stripe.com/docs/currencies#zero-decimal
    var int_currencies = [
        'BIF', 'XAF', 'XPF', 'CLP', 'KMF', 'DJF', 'GNF', 'JPY', 'MGA', 'PYG',
        'RWF', 'KRW', 'VUV', 'VND', 'XOF'
    ];

    function getStripeHandler(parentElement)
    {
        var handler = StripeCheckout.configure({
            key: $("input[name='stripe_key']", parentElement).val(),
            image: $("input[name='stripe_image']", parentElement).val(),
            locale: 'auto',
            token: function(token, args) {
                handler.isTokenGenerate = true;
                ajax.jsonRpc("/payment/stripe/create_charge", 'call', {
                    tokenid: token.id,
                    email: token.email,
                    amount: $("input[name='amount']", parentElement).val(),
                    acquirer_id: $("#acquirer_stripe", parentElement).val(),
                    currency: $("input[name='currency']", parentElement).val(),
                    invoice_num: $("input[name='invoice_num']", parentElement).val(),
                    return_url: $("input[name='return_url']", parentElement).val()
                }).done(function(data){
                    handler.isTokenGenerate = false;
                    window.location.href = data;
                }).fail(function(){
                    var msg = arguments && arguments[1] && arguments[1].data && arguments[1].data.message;
                    var wizard = $(qweb.render('stripe.error', {'msg': msg || _t('Payment error')}));
                    wizard.appendTo($('body')).modal({'keyboard': true});
                });
            },
        });
        return handler;
    }

    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_payment_form'");
    }

    var observer = new MutationObserver(function(mutations, observer) {
        for(var i=0; i<mutations.length; ++i) {
            for(var j=0; j<mutations[i].addedNodes.length; ++j) {
                if(mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') == 'stripe') {
                    display_stripe_form($(mutations[i].addedNodes[j]));
                }
            }
        }
    });

    function display_stripe_form(provider_form) {
        var acquirer_id = $('input[name="acquirer"]', provider_form).val();
        var so_id = $("input[name='return_url']", provider_form).val().match(/quote\/([0-9]+)/) || undefined;
        var access_token = $("input[name='return_url']", provider_form).val().match(/quote\/([0-9]+)\/([0-9a-zA-Z\-]+)/) || undefined;
        if (so_id) {
            so_id = parseInt(so_id[1]);
        }
        if(access_token) {
            access_token = access_token[2];
        }

        if ($('.o_website_payment').length !== 0) {
            var currency = $("input[name='currency']", provider_form).val();
            var amount = parseFloat($("input[name='amount']", provider_form).val() || '0.0');
            if (!_.contains(int_currencies, currency)) {
                amount = amount*100;
            }

            ajax.jsonRpc('/website_payment/transaction', 'call', {
                    reference: $("input[name='invoice_num']", provider_form).val(),
                    amount: amount,
                    currency_id: currency,
                    acquirer_id: acquirer_id
                })
                var handler = getStripeHandler(provider_form);
                handler.open({
                    name: $("input[name='merchant']", provider_form).val(),
                    description: $("input[name='invoice_num']", provider_form).val(),
                    currency: currency,
                    amount: amount,
                });
        } else {
            var currency = $("input[name='currency']", provider_form).val();
            var amount = parseFloat($("input[name='amount']", provider_form).val() || '0.0');
            if (!_.contains(int_currencies, currency)) {
                amount = amount*100;
            }

            var url = '/shop/payment/transaction/';
            if(so_id) {
                url += so_id + '/';
                if(access_token) {
                    url += access_token;
                }
            }

            ajax.jsonRpc(url, 'call', {
                    acquirer_id: acquirer_id
                }, {'async': false}).then(function (data) {
                provider_form[0].innerHTML = data;
                var handler = getStripeHandler(provider_form);
                handler.open({
                    name: $("input[name='merchant']", provider_form).val(),
                    description: $("input[name='invoice_num']", provider_form).val(),
                    currency: currency,
                    amount: amount,
                });
            });
        }
    }
    $.getScript("https://checkout.stripe.com/checkout.js", function(data, textStatus, jqxhr) {
        observer.observe(document.body, {childList: true});
        display_stripe_form($('form[provider="stripe"]'));
    });

});
