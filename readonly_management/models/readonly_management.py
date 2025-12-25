# -*- coding: utf-8 -*-
import logging

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
