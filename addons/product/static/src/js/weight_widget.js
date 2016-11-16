odoo.define('product.weight_widget', function (require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var form_widgets = require('web.form_widgets');
var kanban_widgets = require('web_kanban.widgets');
var Model = require('web.Model');
var session = require('web.session');

var QWeb = core.qweb;
var _t = core._t;

var WeightWidgetForm = form_widgets.FieldFloat.extend({
    template: 'FieldWeight',
    initialize_content: function() {
        this._super();
        if (!this.get('effective_readonly')) {
            this.$input = this.$('input');
            this.add_symbol();
        } else {
            this.$input = undefined;
        }
    },
    add_symbol: function() {
        if (session.weight_uom.name) {
            this.$el.append($('<span/>', {html: ' ' + session.weight_uom.name}));
        }
    },
    render_value: function() {
        var show_value = this.format_value(this.get('value') * session.weight_uom.factor, '');
        this._super();
        if (this.get('effective_readonly')) {
            this.$el.text(show_value);
            this.add_symbol();
        } else {
            this.$input.val(show_value);
        }
    },
    get_digits_precision: function() {
        return this.node.attrs.digits || this.field.digits || session.weight_uom.digits;
    },
    format_value: function(val, def) {
        return formats.format_value(val, {type: "float", digits: this.get_digits_precision()}, def);
    },
    internal_set_value: function(value_) {
        return this._super(value_ / session.weight_uom.factor);
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
