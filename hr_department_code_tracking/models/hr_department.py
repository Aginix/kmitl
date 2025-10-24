# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    code = fields.Char(tracking=True)
