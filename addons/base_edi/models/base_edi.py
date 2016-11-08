# -*- coding: utf-8 -*-

from os.path import dirname, join, basename
import jinja2
from StringIO import StringIO
from lxml import etree
from odoo import models, fields, api, tools, exceptions

class BaseJinja:
    def _edi_load_business_document(self, template_path, template_data):
        ''' This method loads the right template and fills it with
        data passed as parameter. This step is done using jinja2.
        '''
        addons_dir = join(dirname(tools.config['root_path']), 'addons')
        template_dir = join(addons_dir, dirname(template_path))
        template_name = basename(template_path)
        loader = jinja2.FileSystemLoader(template_dir)
        environment = jinja2.Environment(
            loader=loader,
            trim_blocks=True, 
            lstrip_blocks=True
            )
        template = environment.get_template(template_name)
        xml_content = template.render(template_data)
        return xml_content


class BaseEtree:
    def _edi_create_str_from_tree(self, xml_tree):
        ''' Transforms a node tree into a well indended string.
        '''
        return etree.tostring(
            xml_tree, 
            pretty_print=True, 
            encoding='UTF-8',
            xml_declaration=True)

    def _edi_check_validity(self, xml_tree, xml_schema):
        ''' Checks the validity of the node tree according to the schema.
        '''
        if not xml_schema.validate(xml_tree):
            raise exceptions.UserError('The generate file is unvalid')

    def _edi_create_xml_tree(self, xml_content):
        ''' Transforms the content of the template into a node tree.
        '''
        xml_parser = etree.XMLParser(remove_blank_text=True)
        xml_doc_str = xml_content.encode('utf-8')
        xml_tree = etree.fromstring(xml_doc_str, parser=xml_parser)
        return xml_tree

    def _edi_load_xml_schema(self, xsd_path):
        ''' Load the xml schema from file.
        '''
        xml_schema_doc = etree.parse(tools.file_open(xsd_path))
        xml_schema = etree.XMLSchema(xml_schema_doc)
        return xml_schema

    def _edi_create_business_tree_node(self, xml_content, xsd_path=None):
        ''' Generates the tree node and checks it's validity.
        '''
        xml_tree = self._edi_create_xml_tree(xml_content)
        if xsd_path:
            xml_schema = self._edi_load_xml_schema(xsd_path)
            self._edi_check_validity(xml_tree, xml_schema)
        return xml_tree

class BaseEdi(models.Model, BaseJinja, BaseEtree):
    _name = 'base.edi'

    @api.model
    def edi_generate_invoice_attachments(self):
        ''' Abstract method that is called when the business documents can
        be created as attachments. So, this method must be overrided for each
        king of documents.
        '''
        return

    @api.model
    def edi_create_template_data(self):
        ''' This method returns the dictionary that will be used by jinja to fill
        the templates. This dictionary can contains various features of python like
        functions, lambda, etc.
        '''
        return {'item': self}

    @api.model
    def _edi_create_attachment_content(self, template_path, xsd_path=None):
        ''' This method is in charge to generate/fill/check the template and to
        return the content that will be added as attachment.
        '''
        template_data = self.edi_create_template_data()
        business_document = \
            self._edi_load_business_document(template_path, template_data)
        business_document_tree = \
            self._edi_create_business_tree_node(business_document, xsd_path)
        business_document_content = \
            self._edi_create_str_from_tree(business_document_tree)
        return business_document_content

    @api.model
    def edi_create_attachment(self, filename, template_path, xsd_path=None):
        ''' Creates an edi attachment.
        '''
        content = self._edi_create_attachment_content(template_path, xsd_path)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'res_id': self.id,
            'res_model': unicode(self._name),
            'datas': content.encode('base64'),
            'datas_fname': filename,
            'type': 'binary',
            })