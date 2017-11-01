odoo.define('hr_expense.FormController', function (require) {
"use strict";

var core = require('web.core');
var FormController = require('web.FormController');

var _t = core._t;

FormController.include({

    custom_events: _.extend({}, FormController.prototype.custom_events, {
        attachment_clicked: '_onAttachClicked',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onAttachClicked: function (ev) {
        ev.stopPropagation();
        var self = this,
            attrs = ev.data.attrs;
        if (attrs.special === 'attachdocument') {
            var canBeSaved = self.canBeSaved(ev.data.record.id);
            if (canBeSaved && !ev.data.record.res_id) {
                self.do_warn(_t('Warning : need to save your record for attach document!'));
            }
            return canBeSaved;
        }
    },
});

});
