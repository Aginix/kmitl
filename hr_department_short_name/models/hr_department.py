# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    short_name = fields.Char(string='Short Name', tracking=True)
