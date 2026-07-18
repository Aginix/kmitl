# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    sarabun_officer_ids = fields.Many2many(
        comodel_name="res.users",
        relation="sarabun_department_officer_rel",
        column1="department_id",
        column2="user_id",
        string="ธุรการหน่วยงาน (Unit Clerks)",
        help="Users who act for this unit's document office (ธุรการหน่วยงาน) when a "
        "routing step targets the department (ธุรการหน่วยงาน mode). May be more than "
        "one (first-to-act).",
    )
    sarabun_officer_count = fields.Integer(
        string="ธุรการหน่วยงาน",
        compute="_compute_sarabun_officer_count",
    )

    @api.depends("sarabun_officer_ids")
    def _compute_sarabun_officer_count(self):
        for dept in self:
            dept.sarabun_officer_count = len(dept.sarabun_officer_ids)

    def _saraban_central_users(self):
        """Resolve the users who act for this unit (ธุรการหน่วยงาน routing target).

        Falls back to the department manager's user when no clerk is set. The
        manager is an hr.employee (not readable by a plain user), so the fallback
        is read with sudo — this method feeds the live holder preview shown while
        merely viewing/editing a document, and must never raise AccessError.
        """
        self.ensure_one()
        users = self.sarabun_officer_ids
        if not users:
            manager = self.sudo().manager_id
            if manager and manager.user_id:
                users = manager.user_id
        return users
