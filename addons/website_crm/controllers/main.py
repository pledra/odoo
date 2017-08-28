from openerp.addons.website_form.controllers.main import WebsiteForm


class WebsiteCrmForm(WebsiteForm):

    def insert_record(self, request, model, values, custom, meta=None):
        record_id = super(WebsiteCrmForm, self).insert_record(request, model, values, custom, meta)
        if model.model == 'crm.lead':
            request.env[model.model].message_post(body=values['description'], subject=values['name'], message_type='mt_lead_create')
        return record_id
