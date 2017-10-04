odoo.define('mail.ir_attachment_preview', function (require) {

var KanbanView = require('web.KanbanView');
var KanbanRenderer = require('web.KanbanRenderer');
var DocumentViewer = require('mail.DocumentViewer');
var view_registry = require('web.view_registry');

var KanbanAttachmentRenderer = KanbanRenderer.extend({
    events: _.extend({}, KanbanRenderer.prototype.events, {
        'click .o_image_overlay, .o_attachment_preview, .o_play_button, .o_view_button ': '_openAttachmentPreview',
        'click .o_download_content': '_downloadContent',
    }),
    /**
     * Open preview of attachment using document_viewer widget
     * @private
     */
    _openAttachmentPreview: function (event) {
        event.stopPropagation();
        var activeAttachmentID = $(event.currentTarget).closest('.oe_kanban_global_click').data().record.recordData.id;
        var attachments = _.map(this.widgets, function(el){ return el.recordData; });
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, attachments, activeAttachmentID);
            attachmentViewer.prependTo($('body'));
        }
    },
    /**
     * @private
     */
    _downloadContent: function (event) {
        /* disable propagation for preventing clicks on kanban containing images */
        event.stopPropagation();
    },
});

var KanbanAttachemntView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: KanbanAttachmentRenderer,
    }),
});

view_registry.add('kanban_attachment_preview', KanbanAttachemntView);

return {
    Renderer: KanbanAttachmentRenderer,
};
});
