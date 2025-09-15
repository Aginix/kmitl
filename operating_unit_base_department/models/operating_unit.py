# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class OperatingUnit(models.Model):
    _inherit = 'operating.unit'

    department_id = fields.Many2one('hr.department', string='Department', ondelete='restrict', index=True)
