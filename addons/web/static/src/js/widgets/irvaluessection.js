odoo.define('web.IrValuesSection', function (require) {
    "use strict";

    var core = require('web.core');
    var data = require('web.data');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var pyeval = require('web.pyeval');
    var session = require('web.session');
    var Widget = require('web.Widget');

    var QWeb = core.qweb;
    var _t = core._t;

    var IrValuesSection = Widget.extend({
        template: 'IrValuesSection',

        events: {
            'click a:not(.dropdown-toggle)': function (e) {
                var index = $(e.target).data('index');
                var item = this.items[index];
                if (item.callback) {
                    item.callback.apply(this, [item]);
                } else if (item.action) {
                    this.on_item_action_clicked(item);
                } else if (item.url) {
                    return true;
                }
                e.preventDefault();
            },
        },

        init: function (parent, name, label, items, options) {
            this._super.apply(this, arguments);

            this.name = name;
            this.label = label;
            this.items = items;
            this.options = _.defaults(options || {}, {
                editable: true,
            });
        },

        renderElement: function () {
            this._super.apply(this, arguments);

            if (this.$el.children().length === 0 || (this.$('ul').length && this.$('ul').children().length === 0)) {
                this.$el.addClass('o_hidden');
            }

            this.$('.btn').addClass((this.getParent().fields_view.type == 'form')? 'btn-link' : 'btn-primary');

            this.$("[title]").tooltip({
                delay: { show: 500, hide: 0}
            });
        },

        on_item_action_clicked: function (item) {
            var self = this;
            var view_controller = self.getParent();
            view_controller.sidebar_eval_context().done(function (sidebar_eval_context) {
                var ids = view_controller.get_selected_ids();
                var domain;
                if (view_controller.get_active_domain) {
                    domain = view_controller.get_active_domain();
                }
                else {
                    domain = $.Deferred().resolve(undefined);
                }
                if (ids.length === 0) {
                    new Dialog(this, {title: _t("Warning"), size: 'medium', $content: $("<div/>").html(_t("You must choose at least one record."))}).open();
                    return false;
                }
                var dataset = view_controller.dataset;
                var active_ids_context = {
                    active_id: ids[0],
                    active_ids: ids,
                    active_model: dataset.model,
                };

                $.when(domain).done(function (domain) {
                    if (domain !== undefined) {
                        active_ids_context.active_domain = domain;
                    }
                    var c = pyeval.eval('context',
                    new data.CompoundContext(
                        sidebar_eval_context, active_ids_context));

                    self.rpc("/web/action/load", {
                        action_id: item.action.id,
                        context: new data.CompoundContext(
                            dataset.get_context(), active_ids_context).eval()
                    }).done(function(result) {
                        result.context = new data.CompoundContext(
                            result.context || {}, active_ids_context)
                                .set_eval_context(c);
                        result.flags = result.flags || {};
                        result.flags.new_window = true;
                        self.do_action(result, {
                            on_close: function() {
                                // reload view
                                view_controller.reload();
                            },
                        });
                    });
                });
            });
        },
    });

    return IrValuesSection;
});
