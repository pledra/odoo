odoo.define('document.document', function (require) {
    "use strict";

    var core = require('web.core');
    var data = require('web.data');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var FormView = require('web.FormView');
    var IrValuesSection = require('web.IrValuesSection');

    var _t = core._t;

    var IrValuesFileSection = IrValuesSection.extend({
        template: 'IrValuesFileSection',

        events: _.defaults({
            'change .o_sidebar_add_attachment .o_form_binary_form': function (e) {
                var $e = $(e.target);
                if ($e.val() !== '') {
                    this.$('form.o_form_binary_form').submit();
                    $e.parent().find('input[type=file]').prop('disabled', true);
                    $e.parent().find('button').prop('disabled', true).find('img, span').toggle();
                    this.$('.o_sidebar_add_attachment a').text(_t('Uploading...'));
                    framework.blockUI();
                }
            },
            'click .o_sidebar_delete_attachment': function (e) {
                var self = this;
                e.preventDefault();
                e.stopPropagation();
                var $e = $(e.currentTarget);
                var options = {
                    confirm_callback: function () {
                        new data.DataSet(self, 'ir.attachment')
                            .unlink([parseInt($e.attr('data-id'), 10)])
                            .done(function() {
                                self.do_attachment_update(self.dataset, self.model_id);
                            });
                    }
                };
                Dialog.confirm(this, _t("Do you really want to delete this attachment ?"), options);
            },
        }, IrValuesSection.prototype.events),

        init: function () {
            this._super.apply(this, arguments);
            var self = this;

            this.fileupload_id = _.uniqueId('oe_fileupload');
            $(window).on(this.fileupload_id, function() {
                var args = [].slice.call(arguments).slice(1);
                self.do_attachment_update(self.dataset, self.model_id,args);
                framework.unblockUI();
            });
        },
        do_attachment_update: function (dataset, model_id, args) {
            var self = this;
            this.dataset = dataset;
            this.model_id = model_id;
            if (args && args[0].error) {
                this.do_warn(_t('Uploading Error'), args[0].error);
            }
            if (!model_id) {
                on_attachments_loaded([]);
            } else {
                var dom = [ ['res_model', '=', dataset.model], ['res_id', '=', model_id], ['type', 'in', ['binary', 'url']] ];
                var ds = new data.DataSetSearch(this, 'ir.attachment', dataset.get_context(), dom);
                ds.read_slice(['name', 'url', 'type', 'create_uid', 'create_date', 'write_uid', 'write_date'], {}).done(on_attachments_loaded);
            }

            function on_attachments_loaded(attachments) {
                //to display number in name if more then one attachment which has same name.
                _.chain(attachments)
                     .groupBy(function(attachment) { return attachment.name; })
                     .each(function(attachment){
                         if(attachment.length > 1)
                             _.map(attachment, function(attachment, i){
                                 attachment.name = _.str.sprintf(_t("%s (%s)"), attachment.name, i+1);
                             });
                      });
                
                _.each(attachments,function(a) {
                    a.label = a.name;
                    if(a.type === "binary") {
                        a.url = '/web/content/'  + a.id + '?download=true';
                    }
                });
                self.items = attachments;
                self.renderElement();
            }
        },
    });

    FormView.include({
        init: function () {
            this._super.apply(this, arguments);
            this.ir_values_sections.files = {label: _t('Attachment(s)'), klass: IrValuesFileSection};
        },
        record_created: function () {
            var self = this;
            return $.when(this._super.apply(this, arguments)).then(function () {
                if (self.options.sidebar) {
                    self.ir_values_sections.files.instance.do_attachment_update(self.dataset, self.datarecord.id);
                }
            });
        },
        load_record: function () {
            var self = this;
            return $.when(this._super.apply(this, arguments)).then(function () {
                if (self.options.sidebar) {
                    self.ir_values_sections.files.instance.do_attachment_update(self.dataset, self.datarecord.id);
                }
            });
        },
    });

    return IrValuesFileSection;
});
