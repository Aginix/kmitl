# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class KmitlProjectReserveConfirm(models.TransientModel):
    _name = "kmitl.project.reserve.confirm"
    _description = "ยืนยันงบประมาณที่ได้รับจัดสรร"

    project_id = fields.Many2one("kmitl.project", required=True)

    def action_confirm(self):
        self.ensure_one()
        project = self.project_id
        if project.state != "to_verify":
            raise UserError(_("ยืนยันงบประมาณได้เฉพาะสถานะรอจัดสรรงบประมาณ"))
        project._check_budget_plan_lines()
        # The commitment is reserved at approval, not here (ADR-0010).
        project.write({"state": "to_send"})
