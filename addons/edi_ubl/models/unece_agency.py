# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

class UneceAgency(models.Model):
    ''' Represents an agency of 
    United Nations Economic Commission for Europe (UNECE).
    '''
    _name = 'unece.agency'

    code = fields.Integer(string='Code', index=True)
    name = fields.Char(string='Name', index=True)
    description = fields.Char(string='Description')


class UneceType(models.Model):
    ''' An UNECE type defines a sub-group of UNECE code for
    each agency.
    '''
    _name = 'unece.type'

    agency_id = fields.Many2one('unece.agency', required=True)
    name = fields.Char(string='Name', index=True)


class UneceCode(models.Model):
    ''' The UNECE codes are provided in the official website but are not all
    implemented in Odoo: www.unece.org
    '''
    _name = 'unece.code'

    type_id = fields.Many2one('unece.type', required=True)
    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Char(string='Description')

    _sql_constraints = [(
        'type_code_uniq',
        'unique(code, name)',
        'An UN/ECE code of the same type already exists'
        )]
