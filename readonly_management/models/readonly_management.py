# -*- coding: utf-8 -*-
import json
import logging

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ReadonlyManagement(models.Model):
    _name = 'readonly.management'
    _description = 'Readonly Management'

    name = fields.Char('Name')
    model = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    field_ids = fields.Many2many(
        'ir.model.fields',
        string='Fields',
        domain="[('model_id', '=', model)]",
        required=True,
    )
    model_name = fields.Char(
        related='model.model',
        store=False,
        readonly=True
    )
    domain = fields.Char()
