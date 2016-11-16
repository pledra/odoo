# -*- coding: utf-8 -*-

from os.path import dirname, join, basename
from StringIO import StringIO
from lxml import etree
from odoo import models, fields, api, tools
from odoo.exceptions import UserError
from tempfile import NamedTemporaryFile
import PyPDF2

class BaseEtree:
    def edi_as_str(self, xml_tree):
        ''' Transforms a node tree into a well indended string.
        '''
        return etree.tostring(
            xml_tree, 
            pretty_print=True, 
            encoding='UTF-8',
            xml_declaration=True)

    def edi_as_tree(self, document):
        ''' Transforms the content of the template into a node tree.
        '''
        xml_parser = etree.XMLParser(remove_blank_text=True)
        xml_content = document.encode('utf-8')
        xml_tree = etree.fromstring(xml_content, parser=xml_parser)
        return xml_tree

    def edi_as_schema(self, xsd_path):
        ''' Load the xml schema from file.
        '''
        xml_schema_doc = etree.parse(tools.file_open(xsd_path))
        xml_schema = etree.XMLSchema(xml_schema_doc)
        return xml_schema

class BaseEdi(models.Model, BaseEtree):
    _name = 'base.edi'

    @api.model
    def edi_generate_attachments(self):
        ''' Abstract method that is called when the business documents can
        be created as attachments. So, this method must be overrided for each
        king of documents.
        '''
        return

    @api.model
    def edi_as_subvalues(self, dictionary):
        ''' This method is usefull to bring more genericity during the rendering.
        Sometimes, a subtemplate can get its values from a object or a dictionnary but
        this is not supported by Qweb. So, this method create an object from a dict.
        '''
        class SubValues:
            def __init__(self, dictionary):
                for key, value in dictionary.items():
                    setattr(self, key, value)
        return SubValues(dictionary)

    @api.model
    def edi_check_tree_validity(self, tree, xsd_path=None):
        if xsd_path:
            schema = self.edi_as_schema(xsd_path)
            try:
                schema.assertValid(tree)
            except etree.DocumentInvalid, xml_errors:
                raise UserError('The generate file is unvalid:\n' + 
                    str(xml_errors.error_log))

    @api.model
    def edi_load_rendered_template(
        self, xml_id, values, xsd_path=None, as_tree=False, ns_refactoring=None):
        ''' Load a template.
        '''
        # Rendering
        qweb = self.env['ir.qweb']
        content = qweb.render(xml_id, values=values)

        # Recompute the right namespaces
        if ns_refactoring:
            for key, value in ns_refactoring.items():
                content = content.replace(key, value + ':')

        # Rebuild the tree and check its validity
        tree = self.edi_as_tree(content)
        self.edi_check_tree_validity(tree, xsd_path=xsd_path)

        if as_tree:
            return tree
        return self.edi_as_str(tree)

    @api.model
    def edi_create_attachment(
        self, xml_filename, xml_id=None, values=None, xsd_path=None, content_tree=None, content=None, ns_refactoring=None):
        ''' Creates an edi attachment.
        '''
        # Look about the content or create it if necessary
        if not content:
            if content_tree:
                self.edi_check_tree_validity(content_tree, xsd_path=xsd_path)
                content = self.edi_as_str(content_tree)
            elif xml_id:
                content = self.edi_load_rendered_template(
                    xml_id, 
                    values=values, 
                    xsd_path=xsd_path, 
                    ns_refactoring=ns_refactoring)
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