odoo.define('product.uom_widget_form', function (require) {
"use strict";

var formats = require('web.formats');
var form_widgets = require('web.form_widgets');

var UomWidgetForm = form_widgets.FieldFloat.extend({
    /*  Template for widgets displaying values in different unit of measures
        Extend by adding a this.uom_data object in the init function.
        It should contain:
            'name': <unit_name>,
            'factor': <unit_conversion_factor>, (compared to the stored value in the DB, -> if value is stored in kg, grams will have factor 1000)
            'digits': [<max_digits_before_comma>, <digits_after_comma>]
        E.g.: this.uom_data = {'name': 'cm', 'factor': 100, digits: [69, 0]}
    */
    template: 'FieldUom',
    init: function() {
        this._super.apply(this, arguments);
        if (!this.uom_data) {
            this.uom_data = {'name': '', 'factor': 1, digits: [69, 3]};
        }
    },
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
        this.$el.append($('<span/>', {html: ' ' + this.uom_data.name}));
    },
    render_value: function() {
        var show_value = this.format_value(this.get('value') * this.uom_data.factor, '');
        this._super();
        if (this.get('effective_readonly')) {
            this.$el.text(show_value);
            this.add_symbol();
        } else {
            this.$input.val(show_value);
        }
    },
    get_digits_precision: function() {
        return this.node.attrs.digits || this.field.digits || this.uom_data.digits;
    },
    format_value: function(val, def) {
        return formats.format_value(val, {type: "float", digits: this.get_digits_precision()}, def);
    },
    internal_set_value: function(value_) {
        // value_ can either be a string or a number, if it's a string we parse it before applying the conversion factor
        if (typeof(value_) == "string"){
            value_ = formats.parse_value(value_, {type: "float"}, 0);
        }
        return this._super(value_ / this.uom_data.factor);
    },
});

return UomWidgetForm;

});
