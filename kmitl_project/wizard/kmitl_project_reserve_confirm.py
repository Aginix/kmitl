# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class KmitlProjectReserveConfirm(models.TransientModel):
    _name = "kmitl.project.reserve.confirm"
    _description = "จองงบประมาณ — ยืนยัน"

    project_id = fields.Many2one("kmitl.project", required=True)
    budget_account_id = fields.Many2one(
        "budget.account", related="project_id.budget_account_id", string="รหัสงบประมาณ"
    )
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year", related="project_id.account_fiscal_year_id", string="ปีงบประมาณ"
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account", related="project_id.activity_analytic_id", string="กิจกรรม"
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account", related="project_id.department_analytic_id", string="ส่วนงาน"
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account", related="project_id.fund_analytic_id", string="กองทุน"
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account", related="project_id.source_analytic_id", string="แหล่งเงิน"
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        related="project_id.analytic_account_id",
        string="มิติโครงการ",
    )
    budget_amount = fields.Float(
        related="project_id.budget_amount", string="งบประมาณที่ได้รับจัดสรร"
    )

    def action_confirm(self):
        self.ensure_one()
        project = self.project_id
        if project.state != "to_verify":
            raise UserError(_("จองงบประมาณได้เฉพาะสถานะรอตรวจสอบ"))
        project._check_budget_plan_lines()
        project._reserve_project_commitment()
        project.write({"state": "to_send"})
