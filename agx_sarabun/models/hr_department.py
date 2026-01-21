# -*- coding: utf-8 -*-
from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    sarabun_officer_ids = fields.Many2many(
        comodel_name="res.users",
        relation="hr_department_sarabun_officer_rel",
        column1="department_id",
        column2="user_id",
        string="Sarabun Officers",
        help="Users who can receive and process sarabun documents for this department. "
        "If not set, the department manager will receive documents.",
    )
