# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
import uuid

class BaseEdi(models.Model):
    _inherit = 'base.edi'

    UBL_COUNTRIES = [
        'BE',
    ]

    UBL_NAMESPACES = {
        'cac': '{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}',
        'cbc': '{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}',
    }

    ''' UBL_NS_REFACTORING is used to restore the right namespaces inside the xml.
    This method is necessary when using Qweb because the <t></t> elements cause some 
    troubles when some namespaces are specified to etree. So, to avoid this problem,
    the namespaces are encoded with a prefix in each tag and can be replaced as a namespace definition
    after the Qweb rendering. In this case, the prefix is 'cbc__' or 
    'cac__' and is replaced by 'cbc:' or 'cac:' respectively.
    '''
    UBL_NS_REFACTORING = {
        'cbc__': 'cbc',
        'cac__': 'cac',
    }

    @api.model
    def _ubl_get_uuid(self):
        '''UBL recommendations:
        - UUID should be used whenever possible.
        - When using UUID in a document, it is important that the UUID is 
        generated every time the document is generated, i.e. this UUID 
        identifies this instance specifically.
        '''
        return uuid.uuid1()

    @api.model
    def ubl_create_values(self):
        ''' This method returns the dictionary that will be used by to fill
        the templates.
        '''
        return {
            'get': lambda o, f: getattr(o, f, None),
            'version_id': 2.1,
            'uuid': self._ubl_get_uuid(),
            'currency_name': self.currency_id.name,
            'supplier_party': self.company_id.partner_id.commercial_partner_id,
            'customer_party': self.partner_id.commercial_partner_id,
        }