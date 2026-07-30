# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    # === เล่มทะเบียนหนังสือ (register books — ADR-0011) ===
    sarabun_sequence_ids = fields.One2many(
        comodel_name="sarabun.document.sequence",
        inverse_name="sender_department_id",
        string="เล่มทะเบียนหนังสือ (Registers)",
        help="เล่มทะเบียนที่หน่วยงานนี้ใช้ออกเลขหนังสือ — มีได้หลายเล่ม.",
    )
    default_sarabun_sequence_id = fields.Many2one(
        comodel_name="sarabun.document.sequence",
        string="เล่มทะเบียนหลัก (Default Register)",
        domain="[('sender_department_id', '=', id)]",
        help="เล่มทะเบียนที่ใช้เป็นค่าเริ่มต้นเมื่อสร้างหนังสือของหน่วยงานนี้ "
        "เพื่อไม่ต้องเลือกทุกครั้ง (ผู้จัดทำยังเปลี่ยนเป็นเล่มอื่นได้ก่อนส่ง).",
    )

    @api.constrains("default_sarabun_sequence_id")
    def _check_default_sarabun_sequence(self):
        for dept in self:
            seq = dept.default_sarabun_sequence_id
            if seq and seq.sender_department_id != dept:
                raise ValidationError(_(
                    "เล่มทะเบียนหลักต้องเป็นเล่มทะเบียนของหน่วยงาน '%s' เอง."
                ) % dept.display_name)

    @api.depends("sarabun_officer_ids")
    def _compute_sarabun_officer_count(self):
        for dept in self:
            dept.sarabun_officer_count = len(dept.sarabun_officer_ids)

    def _sarabun_registers(self):
        """The unit's active เล่มทะเบียน (searched, not via the o2m, so an archived
        book never leaks in through the cache)."""
        self.ensure_one()
        return self.env["sarabun.document.sequence"].search([
            ("sender_department_id", "=", self.id),
            ("active", "=", True),
        ])

    def _sarabun_default_sequence(self):
        """The เล่มทะเบียน a new หนังสือ of this unit issues from: the configured
        เล่มทะเบียนหลัก, else the unit's only register. Empty when the unit has no
        register at all, or several with no default set (the drafter must pick)."""
        self.ensure_one()
        default = self.default_sarabun_sequence_id
        if default and default.active:
            return default
        registers = self._sarabun_registers()
        return registers if len(registers) == 1 else registers[:0]

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
