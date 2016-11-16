odoo.define('product.weight_widget', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var form_widgets = require('web.form_widgets');
var kanban_widgets = require('web_kanban.widgets');
var session = require('web.session');

var UomWidgetForm = require('product.uom_widget_form');

var WeightWidgetForm = UomWidgetForm.extend({
    init: function() {
        this.uom_data = session.weight_uom;
        this._super.apply(this, arguments);
    },
});

var WeightWidgetKanban = kanban_widgets.AbstractField.extend({
    tagName: 'span',
    renderElement: function() {
        var digits_precision = this.options.digits || session.weight_uom.digits;
        var value = formats.format_value(this.field.raw_value * session.weight_uom.factor || 0, {type: "float", digits: digits_precision}, '0');
        value += ' ' + session.weight_uom.name;
        this.$el.text(value);
    }
});

core.form_widget_registry.add('weight', WeightWidgetForm);
kanban_widgets.registry.add('weight', WeightWidgetKanban);

});
