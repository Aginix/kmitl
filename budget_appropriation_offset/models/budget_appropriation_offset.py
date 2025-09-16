# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationOffset(models.Model):
    _name = _description = "budget.appropriation.offset"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("ชื่อ", tracking=True)
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        tracking=True,
    )
    from_analytic_distribution = fields.Json(string="From Analytic Distribution")
    to_analytic_distribution = fields.Json(string="To Analytic Distribution")
    note = fields.Char(string="หมายเหตุ", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting_to_process", "Waiting to process"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="สถานะ",
        default="draft",
        readonly=True,
        tracking=True,
    )
    amount = fields.Float(string="จำนวนเงิน", tracking=True)

    appropriation_id = fields.Many2one("budget.appropriation", related="appropriation_line_id.appropriation_id", store=True)
    appropriation_line_id = fields.Many2one("budget.appropriation.line")
    from_department_analytic_id = fields.Many2one(
        "account.analytic.account", string="ส่วนงานต้นทาง", domain=[("root_plan_id.code", "=", "departments")]
    )
    to_department_analytic_id = fields.Many2one(
        "account.analytic.account", string="ส่วนงานปลายทาง", domain=[("root_plan_id.code", "=", "departments")]
    )
    source_analytic_id = fields.Many2one("account.analytic.account", string="แหล่งเงิน")
