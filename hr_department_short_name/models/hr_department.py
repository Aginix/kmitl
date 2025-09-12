# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    short_name = fields.Char(string='Short Name')
