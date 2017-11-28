odoo.define('web_settings_dashboard_auth_token', function (require) {
"use strict";

var Widget = require('web.Widget');
var Dashboard = require('web_settings_dashboard').Dashboard;

Dashboard.include({
    init: function(){
        var res = this._super.apply(this, arguments);
        this.all_dashboards.push('auth_token');
        return res;
    },
    
    load_auth_token: function(data) {
        return new DashboardAuthToken(this, data.auth_token).replace(this.$('.o_web_settings_dashboard_auth_token'));
    },
});

var DashboardAuthToken = Widget.extend({
    template: 'DashboardAuthToken',

    events: {
        'click .o_get_assistance': 'on_get_assistance'
    },

    on_get_assistance: function () {
        this.do_action('auth_token.auth_token_wizard_action_form');
    }

});

return {
    Dashboard: Dashboard,
    DashboardAuthToken: DashboardAuthToken
};
});