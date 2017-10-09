odoo.define('mail.attachment_mixin', function(require) {
"use strict";

var session = require('web.session');
var core = require('web.core');

var QWeb = core.qweb;

var AttachmentMixin = {
    // Attachments
    on_attachment_change: function(event) {
        var self = this,
            files = event.target.files,
            attachments = self.get('attachment_ids');

        self.unlink_duplicate_attachments(files, attachments);
        self.$('form.o_form_binary_form').submit();
        this.$attachment_button.prop('disabled', true);
        var upload_attachments = _.map(files, function(file){
            return {
                'id': 0,
                'name': file.name,
                'filename': file.name,
                'url': '',
                'upload': true,
                'mimetype': '',
            };
        });
        attachments = attachments.concat(upload_attachments);
        self.set('attachment_ids', attachments);
    },
    on_attachment_loaded: function(event) {
        var attachment_ids = [];
        var self = this,
            attachments = this.get('attachment_ids'),
            files = Array.prototype.slice.call(arguments, 1);

        _.each(files, function(file){
            if(file.error || !file.id){
                this.do_warn(file.error);
                attachments = _.filter(attachments, function (attachment) { return !attachment.upload; });
            }else{
                var attachment = _.findWhere(attachments, {filename: file.filename, upload: true});
                if(attachment){
                    attachments = _.without(attachments, attachment);
                    attachments.push({
                        'id': file.id,
                        'name': file.name || file.filename,
                        'filename': file.filename,
                        'mimetype': file.mimetype,
                        'url': session.url('/web/content', {'id': file.id, download: true}),
                    });
                }
            }
        }.bind(this));
        this.set('attachment_ids', attachments);

        _.each(attachments, function(attachment){
             attachment_ids.push(attachment.id);
         });

        self.set_attachment_ids(attachment_ids);
        this.$attachment_button.prop('disabled', false);
    },
    on_attachment_delete: function(event){
        event.stopPropagation();
        var self = this;
        var attachment_id = $(event.target).data("id");

        if (attachment_id) {
            var attachments = [];
             var attachment_ids = [];

            _.each(this.get('attachment_ids'), function(attachment){
                if (attachment_id !== attachment.id) {
                    attachments.push(attachment);
                    attachment_ids.push(attachment.id);
                } else{
                    self.unlink_attachment(attachment.id);
                }
            });
            this.set('attachment_ids', attachments);
            self.set_attachment_ids(attachment_ids);
        }
    },
    _onAttachmentDownload: function (event) {
        event.stopPropagation();
    },
    unlink_duplicate_attachments: function(files, attachments) {},
    unlink_attachment: function(attachment_id) {},
    set_attachment_ids: function(attachment_ids) {},
};
    return AttachmentMixin;

});
