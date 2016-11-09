# -*- coding: utf-8 -*-

from os.path import dirname, join, basename
import jinja2
from StringIO import StringIO
from lxml import etree
from odoo import models, fields, api, tools
from odoo.exceptions import UserError
from tempfile import NamedTemporaryFile
import PyPDF2

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
    def edi_create_str_from_tree(self, xml_tree):
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
            raise UserError('The generate file is unvalid')

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
    def edi_generate_attachments(self):
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
    def edi_create_embedded_pdf_in_xml_content(self, report_name, xml_filename, content):
        ''' This method is usefull when a pdf content need to be embedded in a xml.
        This is the case for the standard e-fff used in belgium.
        '''
        pdf_content = self.env['report'].get_pdf(
            [self.id], report_name, data=self._context)
        original_pdf_file = StringIO(pdf_content)
        original_pdf = PyPDF2.PdfFileReader(original_pdf_file)
        new_pdf_filestream = PyPDF2.PdfFileWriter()
        new_pdf_filestream.appendPagesFromReader(original_pdf)
        new_pdf_filestream.addAttachment(xml_filename, content)
        with NamedTemporaryFile(prefix='odoo-ubl-', suffix='.pdf') as f:
            new_pdf_filestream.write(f)
            f.seek(0)
            pdf_content = f.read()
            f.close()
        return pdf_content.encode('base64')

    @api.model
    def edi_append_block(self, tree_node, block_path, template_data, block_index=None, insert_index=None):
        if not block_index:
            block_index = 0
        if not insert_index:
            insert_index = max(len(tree_node) - 1, 0)
        block_tree_root = self.edi_load_template_tree(block_path, template_data)
        tree_node.insert(insert_index, block_tree_root[block_index])

    @api.model
    def edi_load_template_tree(self, template_path, template_data, xsd_path=None):
        ''' This method is in charge to generate/fill/check the template and to
        return the node tree associated to the xml.
        '''
        business_document = \
            self._edi_load_business_document(template_path, template_data)
        business_document_tree = \
            self._edi_create_business_tree_node(business_document, xsd_path)
        return business_document_tree

    @api.model
    def edi_load_template_content(
        self, template_path, template_data, xsd_path=None):
        ''' This method is in charge to generate/fill/check the template and to
        return the content that will be added as attachment.
        '''
        business_document_tree = \
            self.edi_load_template_tree(template_path, template_data, xsd_path=xsd_path)
        business_document_content = \
            self.edi_create_str_from_tree(business_document_tree)
        return business_document_content

    @api.model
    def edi_create_attachment(
        self, xml_filename, template_path=None, template_data=None, xsd_path=None, content=None):
        ''' Creates an edi attachment.
        '''
        # Look about the content or create it if necessary
        if not content:
            if template_path:
                if not template_data:
                    template_data = self.edi_create_template_data()
                content = self.edi_load_template_content(
                    template_path, template_data, xsd_path=xsd_path)
            else:
                raise UserError('To create an attachment, a template_path or a content must be provided!')
        # Create the attachment      
        attachment = self.env['ir.attachment'].create({
            'name': xml_filename,
            'res_id': self.id,
            'res_model': unicode(self._name),
            'datas': content.encode('base64'),
            'datas_fname': xml_filename,
            'type': 'binary',
            })