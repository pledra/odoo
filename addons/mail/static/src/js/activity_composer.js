odoo.define('mail.activity_composer', function (require) {
"use strict";
var composer = require('mail.composer');
var datepicker = require('web.datepicker');
var FieldManagerMixin = require('web.FieldManagerMixin');
var relational_fields = require('web.relational_fields');
var session = require('web.session');


var ActivityComposer = composer.BasicComposer.extend(FieldManagerMixin, {
    template: 'mail.activity_composer_form',
    events: {
        'click .o_exapand_activity' : '_onFullScheduleActivity',
        'click .o_composer_button_activity': '_onClickScheduleActivity',
        'click .o_composer_button_discard' : '_onClickDiscardActivity',
        'click .o_composer_button_done' : '_onClickMarkDoneActivity',
    },
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        field_changed: '_onFieldChanged',
    }),

    init: function (parent, model, res_id, options) {
        this._super(parent, options);
        FieldManagerMixin.init.call(this);

        this.modelName = model;
        this.res_id = res_id;
        this.activityModel = 'mail.activity';
        this.user_id = session.uid;
    },

    willStart: function () {
        var defs = [this._super.apply(this, arguments), this._defaultGet()];
        return $.when.apply($, defs);
    },

    start: function () {
        this._super.apply(this, arguments);

        var self = this;
        this.activitySummaryInput = this.$('.o_activity_summary');
        this.activityComposer = this.$('.o_composer_activity_text_field');

        this.datewidget = new datepicker.DateWidget(this, {defaultDate: moment()});
        this.datewidget.appendTo(this.$('.date_picker_activity_due_date'));
        this.datewidget.$el.addClass('o_required_modifier');

        this._initM2oFields();

        return $.when().then(function () {
            _.each(self.m2oFields, function (m2oField) {
                self.model.makeRecord(self.modelName, [{
                    name: m2oField.fieldName,
                    relation: m2oField.relation,
                    type: 'many2one',
                    domain: m2oField.domain || [],
                    value: m2oField.value,
                }]).then(function (recordID) {
                    m2oField.el =  new relational_fields.FieldMany2One(self,
                        m2oField.fieldName,
                        self.model.get(recordID),
                        {
                            mode: 'edit',
                            attrs: m2oField.attrs || {},
                       });
                    m2oField.el.appendTo(m2oField.$container);
                    m2oField.el.$('> div').addClass('o_required_modifier');
                });
            });
        });
    },
    /**
     * initialize many2one fields
     *
     * @private
     */
    _initM2oFields: function () {
        var self = this;
        this.m2oFields = {
            user_id: {
                fieldName: 'user_id',
                relation: 'res.users',
                value: self.user_id,
                attrs: {
                    can_create: false,
                    can_write: false,
                    options: { no_open: true }
                },
                $container: self.$('.assigned_user_select_m2o')
            },
            activity_type_id: {
                fieldName: 'activity_type_id',
                relation: 'mail.activity.type',
                domain: ['|', ['res_model_id', '=', false], ['res_model_id', '=', self.res_model_id]],
                attrs: {
                    can_create: false,
                    can_write: false,
                },
                $container: self.$('.activity_type_select_m2o')
            }
        };
    },

    _createActivity: function () {
        var data = this._getData();
        return this._rpc({
            model: this.activityModel,
            method: 'create',
            args: [data]
        });
    },
    /**
     * check required fields and trigger warning
     *
     * @private
     */
    _checkRequiredField: function () {
        var rFields = false;
        if (!this.selectedActivityTypeId) {
            rFields = true;
            this.m2oFields.activity_type_id.el.$input.parent().addClass('o_field_invalid');
            this.do_warn('Please fill required field','Activity');
        }
        if (!this.activityComposer.val()) {
            rFields = true;
            this.do_warn('Please fill required field','Content');
        }
        if (!this.user_id) {
            rFields = true;
            this.m2oFields.user_id.el.$input.parent().addClass('o_field_invalid');
            this.do_warn('Please fill required field','Assigned To');
        }
        if (!this.datewidget.getValue()) {
            rFields = true;
            this.datewidget.$el.addClass('o_field_invalid');
            this.do_warn('Please fill required field','Due Date');
        }
        return !rFields;
    },
    /**
     * return id of current model
     *
     * @private
     */
    _defaultGet: function () {
        var self = this;
        return this._rpc({
            model: 'ir.model',
            method: 'search_read',
            args: [[['model', '=', this.modelName]], ['id']]
        }).then(function (result) {
            self.res_model_id = result[0].id;
        });
    },
    /**
     * return object of all activity data
     *
     * @private
     */
    _getData: function () {
        return {
            res_id: this.res_id,
            res_model_id: this.res_model_id,
            res_model: this.modelName,
            activity_type_id : this.selectedActivityTypeId,
            summary: this.activitySummaryInput.val(),
            date_deadline: this.datewidget.getValue(),
            note: this.activityComposer.val(),
            user_id: this.user_id,
        };
    },
    /**
     * return default data for full activity composer
     *
     * @private
     */
    _getDefaultData: function () {
        var data = {};
        _.each(this._getData(), function (value,key) {
            if (value) {
                data['default_'+key] = value;
            }
        });
        return data;
    },

    _onFullScheduleActivity: function () {
        this.trigger_up('open_activity_full_composer',this._getDefaultData());
        this.trigger.call(this, 'close_composer');
    },

    _updateChatter: function () {
        this.trigger.call(this,'need_refresh');
        this.trigger.call(this, 'close_composer');
    },
    /**
     * set values when on_change called
     *
     * @private
     */
    _resetActivityField: function (result) {
        this.datewidget.setValue(moment(result.value.date_deadline));
        this.activitySummaryInput.val(result.value.summary || '');
    },
    /**
     * activity_type onchange method
     *
     * @private
     */
    _onChangeActivityData: function () {
        var self = this;
        this._rpc({
            model: this.activityModel,
            method: 'onchange',
            args: [[],this._getData(), _.keys(this._getData()) , {'activity_type_id': '1'}],
        }).then(function (result) {
            self._resetActivityField(result);
        });
    },
    /**
     * trigger when many2one fields value is changed
     *
     * @private
     */
    _onFieldChanged: function (event) {
        event.stopPropagation();
        var data = event.data.changes;
        if (data.activity_type_id || data.activity_type_id === false) {
            this.selectedActivityTypeId = data.activity_type_id.id || data.activity_type_id;
            this.m2oFields.activity_type_id.el.$input.val(data.activity_type_id.display_name);
            this._onChangeActivityData();
        }

        if (data.user_id || data.user_id === false) {
            this.user_id = data.user_id.id || data.user_id;
            this.m2oFields.user_id.el.$input.val(data.user_id.display_name);
        }
    },

    _onClickDiscardActivity: function () {
        this.trigger.call(this, 'close_composer');
    },

    _onClickMarkDoneActivity: function () {
        if (this._checkRequiredField()) {
            var self = this;
            this._createActivity().then(function (id) {
                self._rpc({
                    model: self.activityModel,
                    method: 'action_feedback',
                    args: [[id]],
                }).then(function (id) {
                    self._updateChatter();
                });
            });
        }
    },

    _onClickScheduleActivity: function () {
        if (this._checkRequiredField()) {
            var self = this;
            this._createActivity().then(function (id) {
                self._updateChatter();
            });
        }
    }
});

return ActivityComposer;

});
