# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    name = fields.Char(tracking=True)
    parent_id = fields.Many2one(tracking=True)
    manager_id = fields.Many2one(tracking=True)
