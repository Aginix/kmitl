# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class KmitlProjectReserveConfirm(models.TransientModel):
    _name = "kmitl.project.reserve.confirm"
    _description = "จองงบประมาณ — ยืนยัน"

    project_id = fields.Many2one("kmitl.project", required=True)

    def action_confirm(self):
        self.ensure_one()
        project = self.project_id
        if project.state != "to_verify":
            raise UserError(_("จองงบประมาณได้เฉพาะสถานะรอตรวจสอบ"))
        project._check_budget_plan_lines()
        project._reserve_project_commitment()
        project.write({"state": "to_send"})
