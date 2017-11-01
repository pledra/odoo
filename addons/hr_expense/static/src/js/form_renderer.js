odoo.define('hr_expense.FormRenderer', function (require) {
"use static";

var FormRenderer = require('web.FormRenderer');
var AttachDocument = require('hr_expense.Attachment');

FormRenderer.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * The method will be automatically called to replace the button with widget <AttachDocument>.
     * @private
     */
     _renderAttachDocument: function (node, state) {
         // Initialize the widget
         var attachDocument = new AttachDocument(this, {
             'node': node,
             'state': state,
         });
         attachDocument.appendTo($('<span>'));
         return attachDocument.$el;
     },

     /**
      * @override
      * @private
      * @param {Object} node
      * @returns {jQueryElement}
      */
     _renderHeaderButton: function (node) {
         if (node.attrs.special === 'attachdocument') {
            return this._renderAttachDocument(node, this.state);
         }
        return this._super.apply(this, arguments);
     },
});
});
