odoo.define('mail.many2manytags', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var core = require('web.core');
var form_common = require('web.view_dialogs');
var field_registry = require('web.field_registry');
var relational_fields = require('web.relational_fields');

var M2MTags = relational_fields.FieldMany2ManyTags;
var _t = core._t;

BasicModel.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} record - an element from the localData
     * @param {string} fieldName
     * @return {Deferred<Object>} the deferred is resolved with the
     *                            invalidPartnerIds
     */
    _setInvalidMany2ManyTagsEmail: function (record, fieldName) {
        var self = this;
        var localID = (record._changes && fieldName in record._changes) ?
                        record._changes[fieldName] :
                        record.data[fieldName];
        var list = this._applyX2ManyOperations(this.localData[localID]);
        var invalidPartnerIds = [];
        _.each(list.data, function (id) {
            var record = self.localData[id];
            if (!record.data.email) {
                invalidPartnerIds.push(record);
            }
        });
        var def;
        if (invalidPartnerIds) {
            // remove invalid partners
            var changes = {operation: 'DELETE', ids: _.pluck(invalidPartnerIds, 'id')};
            def = this._applyX2ManyChange(record, fieldName, changes);
        }
        return $.when(def).then(function () {
            return $.when({
                invalidPartnerIds: _.pluck(invalidPartnerIds, 'res_id'),
            });
        });
    },
});

var FieldMany2ManyTagsEmail = M2MTags.extend({
    events: _.extend({}, M2MTags.prototype.events, {
        'focusin input': '_onFocusIn',
        'focusout input': '_onFocusOut',
        'click': '_onClick',
    }),
    fieldsToFetch: _.extend({}, M2MTags.prototype.fieldsToFetch, {
        email: {type: 'char'},
    }),
    specialData: "_setInvalidMany2ManyTagsEmail",

    /**
     * @constructor
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.moreThreshold = this.nodeOptions.more_threshold;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Open a popup for each invalid partners (without email) to fill the email.
     *
     * @private
     * @returns {Deferred}
     */
    _checkEmailPopup: function () {
        var self = this;

        var popupDefs = [];
        var validPartners = [];

        // propose the user to correct invalid partners
        _.each(this.record.specialData[this.name].invalidPartnerIds, function (resID) {
            var def = $.Deferred();
            popupDefs.push(def);

            var pop = new form_common.FormViewDialog(self, {
                res_model: self.field.relation,
                res_id: resID,
                context: self.record.context,
                title: _t("Please complete customer's informations and email"),
                on_saved: function (record) {
                    if (record.data.email) {
                        validPartners.push(record.res_id);
                    }
                },
            }).open();
            pop.on('closed', self, function () {
                def.resolve();
            });
        });
        return $.when.apply($, popupDefs).then(function() {
            // All popups have been processed for the given ids
            // It is now time to set the final value with valid partners ids.
            validPartners = _.uniq(validPartners);
            if (validPartners.length) {
                var values = _.map(validPartners, function (id) {
                    return {id: id};
                });
                self._setValue({
                    operation: 'ADD_M2M',
                    ids: values,
                });
            }
        });
    },
    /**
     * Override to check if all many2many values have an email set before
     * rendering the widget.
     *
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        var def = $.Deferred();
        var _super = this._super.bind(this);
        if (this.record.specialData[this.name].invalidPartnerIds.length) {
            def = this._checkEmailPopup();
        } else {
            def.resolve();
        }
        return def.then(function () {
            return _super.apply(self, arguments);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function () {
        this.activate();
    },

    /**
     * @private
     */
    _onFocusIn: function () {
        if (this.$moreText) {
            this.$moreText.remove();
            this.$moreBadges.removeClass('hidden');
        }
    },

    /**
     * @private
     */
    _onFocusOut: function () {
        if (this.moreThreshold && this.$('.badge').length > this.moreThreshold && !$(this.$el).is(':hover')) {
            this.$moreBadges = this.$(_.str.sprintf('.badge:gt(%d)', this.moreThreshold - 1)).addClass('hidden');
            var names = _.map(this.$moreBadges, function (badge) {
                return badge.textContent.trim();
            });
            this.$moreText = $('<span />', {
                class: 'more ml8 mr8',
                title: names.join('\n'),
                text: _.str.sprintf('%d %s', this.$('.badge').length - this.moreThreshold, _t('More'))
            }).insertAfter(this.$('.badge').last());
        }
    },
});

field_registry.add('many2many_tags_email', FieldMany2ManyTagsEmail);

});
