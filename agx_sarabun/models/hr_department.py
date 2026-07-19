# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    sarabun_officer_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="sarabun_department_officer_rel",
        column1="department_id",
        column2="employee_id",
        string="ธุรการหน่วยงาน (Unit Clerks)",
        help="Personnel who act for this unit's document office (ธุรการหน่วยงาน) "
        "when a routing step targets the department (ธุรการหน่วยงาน mode). May be "
        "more than one (first-to-act). Only personnel with a linked user can act.",
    )
    sarabun_officer_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="หน่วยงานธุรการ (Clerk Unit)",
        help="Not every unit runs its own document office. When this unit has no "
        "ธุรการหน่วยงาน of its own, a routing step that targets it falls back to the "
        "clerks of the unit named here (a single hop — that unit's own clerks, else "
        "its manager). Leave empty to fall back to this unit's manager.",
    )
    sarabun_officer_count = fields.Integer(
        string="ธุรการหน่วยงาน",
        compute="_compute_sarabun_officer_count",
    )

    @api.depends("sarabun_officer_ids")
    def _compute_sarabun_officer_count(self):
        for dept in self:
            dept.sarabun_officer_count = len(dept.sarabun_officer_ids)

    def _saraban_central_employees(self):
        """The hr.employee ธุรการหน่วยงาน (for display/preview). Resolution order:
        this unit's own clerks → the delegated หน่วยงานธุรการ's clerks (single hop,
        so A→B→A cannot loop) → the department manager. The delegate/manager reads
        are sudoed — this feeds the live preview shown while merely viewing a
        document and must never raise AccessError for a non-HR user."""
        self.ensure_one()
        employees = self.sarabun_officer_ids
        if not employees and self.sarabun_officer_department_id:
            delegate = self.sarabun_officer_department_id.sudo()
            employees = delegate.sarabun_officer_ids or delegate.manager_id
        if not employees:
            employees = self.sudo().manager_id
        return employees

    def _saraban_central_users(self):
        """res.users who act for this unit (employees → their linked user)."""
        self.ensure_one()
        return self._saraban_central_employees().mapped("user_id")
