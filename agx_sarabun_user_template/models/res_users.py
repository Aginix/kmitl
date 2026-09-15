# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    # Non-stored computed field used by the ir.rule for unit-visibility.
    # Returns the user's department plus all ancestor departments (via parent_path),
    # so a template shared at a parent dept is visible to child-dept members.
    sarabun_shared_department_ids = fields.Many2many(
        "hr.department",
        compute="_compute_sarabun_shared_department_ids",
        compute_sudo=True,
    )

    @api.depends("employee_id.department_id")
    def _compute_sarabun_shared_department_ids(self):
        for user in self:
            dept = user.employee_id.department_id
            ids = []
            if dept and dept.parent_path:
                ids = [int(x) for x in dept.parent_path.split("/") if x]
            user.sarabun_shared_department_ids = [(6, 0, ids)]
