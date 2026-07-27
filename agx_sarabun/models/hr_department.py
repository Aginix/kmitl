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
    is_sarabun_office = fields.Boolean(
        string="หน่วยงานธุรการ (Document Office)",
        help="ติ๊กหากหน่วยงานนี้ทำหน้าที่ธุรการ (รับ-ส่งสารบรรณ). เฉพาะหน่วยงานที่ติ๊ก "
        "เท่านั้นจึงจะถูกเลือกเป็นเป้าหมาย 'ธุรการหน่วยงาน' ในเส้นทางเอกสารได้ — "
        "หน่วยงานที่ไม่ติ๊กจะไม่แสดงในตัวเลือก routing ธุรการหน่วยงาน.",
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
        """The hr.employee ธุรการหน่วยงาน (for display/preview). Falls back to the
        department manager (also an hr.employee) when no clerk is configured. The
        manager read is sudoed — it feeds the live preview shown while merely
        viewing a document and must never raise AccessError for a non-HR user."""
        self.ensure_one()
        employees = self.sarabun_officer_ids
        if not employees:
            employees = self.sudo().manager_id
        return employees

    def _saraban_central_users(self):
        """res.users who act for this unit (employees → their linked user)."""
        self.ensure_one()
        return self._saraban_central_employees().mapped("user_id")
