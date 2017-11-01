odoo.define('hr_expense.Attachment', function (require) {
"use static";

var Mixins = require('web.mixins');
var Widget = require('web.Widget');

var AttachDocument = Widget.extend(Mixins.EventDispatcherMixin, {
    template: 'AttachDocument',
    events: {
        'click #o_attach_document': '_onClickAttachDocument',
        'change input.o_input_file': '_onFileChanged',
    },
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} params
     */
    init: function (parent, params) {
        this.res_id = params.state.res_id;
        this.res_model = params.state.model;
        this.node = params.node;
        this.state = params.state;
        Mixins.EventDispatcherMixin.init.call(this);
        this.fileuploadID = _.uniqueId('o_fileupload');
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        $(window).on(self.fileuploadID, self._onFileLoaded.bind(self));
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        $(window).off(this.fileupload_id);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickAttachDocument: function (ev) {
        // This widget uses a hidden form to upload files. Clicking on 'Attach'
        if (this.res_id && this.getParent().canBeSaved(this.state.id).length === 0) {
            this.$('input.o_input_file').trigger('click');
        } else {
            this.trigger_up('attachment_clicked', {
                 attrs: this.node.attrs,
                 record: this.state,
            });
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFileChanged: function (ev) {
        ev.stopPropagation();
        this.$('form.o_form_binary_form').trigger('submit');
    },
    /**
     * attachdocument log on chatter
     *
     * @private
     */
    _onFileLoaded: function () {
        var self = this;
        // the first argument isn't a file but the jQuery.Event
        var files = Array.prototype.slice.call(arguments, 1);
        return this._rpc({
            model: self.res_model,
            method: 'message_post',
            args: [self.res_id],
            kwargs: {
                'attachment_ids': _.map(files, function (file) {return file.id;}),
            }
        }).then( function (){
            // reload the form view
            self.trigger_up('reload');
        });
    },

});
return AttachDocument;
});
