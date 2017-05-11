odoo.define('google_drive.google_drive', function (require) {
"use strict";

var data = require('web.data');
var Sidebar = require('web.Sidebar');

Sidebar.include({
    _redraw: function(){
        var _super = this._super.bind(this);
        var view = this.getParent();
        if (view.renderer && view.renderer.viewType === "form") {
            var r = this.env;
            if(r.activeIds.length){
                return this.add_gdoc_items(view, r.activeIds[0]).then(function(){
                    _super();
                });
            }
        }
        _super();
    },
    add_gdoc_items: function (view, res_id) {
        var self = this;
        var gdoc_item = _.indexOf(_.pluck(self.items.other, 'classname'), 'oe_share_gdoc');
        if (gdoc_item !== -1) {
            self.items.other.splice(gdoc_item, 1);
        }
        return this._rpc({
            model: 'google.drive.config',
            method: 'get_google_drive_config',
            args: [view.modelName, res_id, {}],
        }).done(function (r) {
            if (!_.isEmpty(r)) {
                _.each(r, function (res) {
                    var already_there = false;
                    for (var i = 0;i < self.items.other.length;i++){
                        if (self.items.other[i].classname === "oe_share_gdoc" && self.items.other[i].label.indexOf(res.name) > -1){
                            already_there = true;
                            break;
                        }
                    }
                    if (!already_there){
                        self._addItems('other', [{
                                label: res.name,
                                config_id: res.id,
                                res_id: res_id,
                                res_model: view.modelName,
                                classname: 'oe_share_gdoc'
                            },
                        ]);
                    }
                });
            }
        });

    },
    on_google_doc: function (doc_item) {
        var self = this;
        var domain = [['id', '=', doc_item.config_id]];
        var fields = ['google_drive_resource_id', 'google_drive_client_id'];
        this._rpc({
                model: 'google.drive.config',
                method: 'search_read',
                args: [domain, fields],
            }).then(function (configs) {
            self._rpc({
                model: 'google.drive.config',
                method: 'get_google_drive_url',
                args: [doc_item.config_id, doc_item.res_id,configs[0].google_drive_resource_id, self.modelName],
            }).done(function (url) {
                if (url){
                    window.open(url, '_blank');
                }
            });
        });
    },
});

});
