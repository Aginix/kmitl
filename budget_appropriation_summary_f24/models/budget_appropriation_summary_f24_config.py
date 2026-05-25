# -*- coding: utf-8 -*-
from odoo import _, fields, models


class BudgetAppropriationSummaryF24Config(models.Model):
    _name = "budget.appropriation.summary.f24.config"
    _description = "F24 Report Configuration"

    name = fields.Char(
        required=True,
        default=lambda self: _("F24 Report Configuration"),
    )
    department_analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="budget_f24_config_department_analytic_rel",
        column1="config_id",
        column2="analytic_id",
        string="หน่วยงานในรายงาน F24",
        domain=[
            ("root_plan_id.code", "=", "departments"),
            ("parent_id", "=", False),
        ],
        help=(
            "เลือกหน่วยงานหลัก (คณะ/วิทยาลัย/โรงเรียน) ที่จะปรากฏในรายงาน F24 "
            "รายงานจะรวมข้อมูลของทุกหน่วยงานย่อยที่อยู่ใต้หน่วยงานที่เลือก "
            "และแสดงผลรวมในแถวเดียวต่อหน่วยงานหลัก"
        ),
    )
