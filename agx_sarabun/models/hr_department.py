# -*- coding: utf-8 -*-
from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    sarabun_officer_ids = fields.Many2many(
        comodel_name="res.users",
        relation="sarabun_department_officer_rel",
        column1="department_id",
        column2="user_id",
        string="สารบรรณกลาง (Registry Clerks)",
        help="Users who act for this unit's central registry (สารบรรณกลาง) when a "
        "routing step targets the department (Unit mode). Mainly used by incoming "
        "หนังสือ (phase-2).",
    )

    def _saraban_central_users(self):
        """Resolve the users who act for this unit (Unit-mode routing target).

        Falls back to the department manager's user when no registry clerk is set.
        """
        self.ensure_one()
        users = self.sarabun_officer_ids
        if not users and self.manager_id and self.manager_id.user_id:
            users = self.manager_id.user_id
        return users
