odoo.define('web.ButtonWidget', function (require) {
"use strict";

var core = require('web.core');
var ViewWidget = require('web.ViewWidget');

var _t = core._t;
var qweb = core.qweb;

var ButtonWidget = ViewWidget.extend({
	template: 'WidgetButton',
	/**
     * Button Widget  class
     *
     * @constructor
     * @param {Widget} parent
     * @param {string} node
     * @param {Object} record A record object (result of the get method of a basic model)
     * @param {Object} [options]
     * @param {string} [options.mode=readonly] should be 'readonly' or 'edit'
     */
	init: function (parent, node, record, options) {
		this._super(parent);

		this.node = node;

		// the datapoint fetched from the model
        this.record = record;

        this.string = this.node.attrs.string;

        if (node.attrs.icon) {
            this.fa_icon = node.attrs.icon.indexOf('fa-') === 0;
        }
	},
	start: function() {
		var self = this;
        this._super.apply(this, arguments);
        this.$el.click(function () {
            self.trigger_up('button_clicked', {
                attrs: self.node.attrs,
                record: self.record,
                callback: function() {
                    self.trigger_up('move_next');
                }
            });
        });
        // TODO: To implement
        // if (this.node.attrs.help || core.debug) {
        //     this._addTooltip();
        // }
        this._addOnFocusAction();
    },
	/**
	 * @override
	 * @returns {jQuery} the focusable checkbox input
	 */
	getFocusableElement: function() {
		return this.$el || $();
	},

    _getFocusTip: function(node) {
        var show_focus_tip = function() {
            var content = node.attrs.on_focus_tip ? node.attrs.on_focus_tip : _.str.sprintf(_t("Press ENTER to %s"), node.attrs.string);
            return content;
        }
        return show_focus_tip;
    },
    _addOnFocusAction: function() {
        var self = this;
        var options = _.extend({
            delay: { show: 1000, hide: 0 },
            trigger: 'focus',
            title: function() {
                return qweb.render('FocusTooltip', {
                    getFocusTip: self._getFocusTip(self.node)
                });
            }
        }, {});
        this.$el.tooltip(options);
    },
    _addTooltip: function(widget, $node) {
    	var self = this;
        this.$el.tooltip({
            delay: { show: 1000, hide: 0 },
            title: function () {
                return qweb.render('WidgetLabel.tooltip', {
                    debug: core.debug,
                    widget: self,
                });
            }
        });
    },
});

return ButtonWidget;

});