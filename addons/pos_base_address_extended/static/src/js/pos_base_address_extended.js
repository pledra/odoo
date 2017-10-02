odoo.define('pos_base_address_extended', function (require) {
"use strict";

var PosScreens = require('point_of_sale.screens');

var ClientListScreenWidget_prototype = PosScreens.ClientListScreenWidget.prototype;
PosScreens.ClientListScreenWidget = PosScreens.ClientListScreenWidget.extend({

    display_client_details: function() {
        this.ClientListScreenWidget_prototype.display_client_details();
        debugger;
        var lol = this.contents.find('section.client-details.edit');
    }
});

});