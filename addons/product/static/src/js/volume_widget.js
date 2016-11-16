odoo.define('product.volume_widget', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var form_widgets = require('web.form_widgets');
var kanban_widgets = require('web_kanban.widgets');
var session = require('web.session');

var UomWidgetForm = require('product.uom_widget_form');

var VolumeWidgetForm = UomWidgetForm.extend({
    init: function() {
        this.uom_data = session.volume_uom;
        this._super.apply(this, arguments);
    },
});

var VolumeWidgetKanban = kanban_widgets.AbstractField.extend({
    tagName: 'span',
    renderElement: function() {
        var digits_precision = this.options.digits || session.volume_uom.digits;
        var value = formats.format_value(this.field.raw_value * session.volume_uom.factor || 0, {type: "float", digits: digits_precision}, '0');
        value += ' ' + session.volume_uom.name;
        this.$el.text(value);
    }
});

core.form_widget_registry.add('volume', VolumeWidgetForm);
kanban_widgets.registry.add('volume', VolumeWidgetKanban);

});
