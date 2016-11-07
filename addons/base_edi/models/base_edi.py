# -*- coding: utf-8 -*-

from os.path import dirname, join, basename
import jinja2
from StringIO import StringIO
from lxml import etree
from odoo import models, fields, api, tools
from odoo.exceptions import ValidationError

class BaseJinja:
    def _load_business_document(self, template_path, template_data):
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
    def _create_str_from_tree(self, xml_tree):
       return etree.tostring(
            xml_tree, 
            pretty_print=True, 
            encoding='UTF-8',
            xml_declaration=True)

    def _check_validity(self, xml_tree, xml_schema):
        assert xml_schema.validate(xml_tree), 'The generate file is unvalid'

    def _create_xml_tree(self, xml_content):
        xml_parser = etree.XMLParser(remove_blank_text=True)
        xml_doc_str = xml_content.encode('utf-8')
        xml_tree = etree.fromstring(xml_doc_str, parser=xml_parser)
        return xml_tree

    def _load_xml_schema(self, xsd_path):
        xml_schema_doc = etree.parse(tools.file_open(xsd_path))
        xml_schema = etree.XMLSchema(xml_schema_doc)
        return xml_schema

    def _create_business_tree_node(self, xml_content, xsd_path=None):
        xml_tree = self._create_xml_tree(xml_content)
        if xsd_path:
            xml_schema = self._load_xml_schema(xsd_path)
            self._check_validity(xml_tree, xml_schema)
        return xml_tree

class BaseEdi(models.Model, BaseJinja, BaseEtree):
    _name = 'base.edi'

    def edi_invoice_validate(self):
        return

    def create_template_data(self):
        return {'item': self}

    def _create_attachment_content(self, template_path, xsd_path=None):
        template_data = self.create_template_data()
        business_document = \
            self._load_business_document(template_path, template_data)
        business_document_tree = \
            self._create_business_tree_node(business_document, xsd_path)
        business_document_content = \
            self._create_str_from_tree(business_document_tree)
        return business_document_content

    def create_attachment(self, filename, template_path, xsd_path=None):
        content = self._create_attachment_content(template_path, xsd_path)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'res_id': self.id,
            'res_model': unicode(self._name),
            'datas': content.encode('base64'),
            'datas_fname': filename,
            'type': 'binary',
            })