odoo.define('auth_token.wizard', function (require) {
"use strict";

var Widget = require('web.Widget');
var core = require('web.core');
var formats = require('web.formats');

var TokenWizard = Widget.extend({
    template: 'auth_token.wizard',
    events: {
            'click .o_remote_close': function (ev) {return this.getParent().destroy();},
    },
    init: function (parent, context) {
        this.url = context.url;
        this.limit_validity = formats.format_value(context.limit_validity, {type: "datetime"});;
        this.user = context.user;
        this.recipients = context.recipients;
        this.email_success = context.email_success;
        return this._super.apply(this, arguments);
    },
    start: function () {
        return this._super.apply(this, arguments);
    },
});

core.action_registry.add('auth_token.wizard', TokenWizard);

return TokenWizard;
});