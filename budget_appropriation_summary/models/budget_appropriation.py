# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    # Inverse M2M needed so Odoo registers field_inverses and propagates
    # amount_net changes back to compilation stored computes.
    revenue_compilation_ids = fields.Many2many(
        comodel_name="budget.appropriation.compilation",
        relation="budget_appropriation_compilation_revenue_rel",
        column1="appropriation_id",
        column2="compilation_id",
        string="รวมเล่ม (รายรับ)",
        copy=False,
    )
    expense_compilation_ids = fields.Many2many(
        comodel_name="budget.appropriation.compilation",
        relation="budget_appropriation_compilation_expense_rel",
        column1="appropriation_id",
        column2="compilation_id",
        string="รวมเล่ม (รายจ่าย)",
        copy=False,
    )

    treasury_replenishment_amount = fields.Monetary(
        string="ชดใช้เงินคงคลัง",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    deducted_reserve_amount = fields.Monetary(
        string="หักเงินสำรอง",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    maintenance_amount = fields.Monetary(
        string="ค่าดูแลและบำรุงรักษา",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    capital_budget_amount = fields.Monetary(
        string="งบลงทุน",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    recurrent_budget_amount = fields.Monetary(
        string="งบประจำ",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    external_funding_amount = fields.Monetary(
        string="เงินสนับสนุนจากหน่วยงานภายนอก",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    code_0702000002 = fields.Monetary(
        string="สำรองจ่ายร้อยละ 15",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    code_0702000003 = fields.Monetary(
        string="สำรองจ่าย เกินกว่าร้อยละ 15",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    recurrent_line_ids = fields.One2many(
        "budget.appropriation.line",
        compute="_compute_flag_line_ids",
        store=False,
        readonly=True,
    )
    ma_line_ids = fields.One2many(
        "budget.appropriation.line",
        compute="_compute_flag_line_ids",
        store=False,
        readonly=True,
    )
    investment_line_ids = fields.One2many(
        "budget.appropriation.line",
        compute="_compute_flag_line_ids",
        store=False,
        readonly=True,
    )

    @api.depends("line_ids.is_recurrent", "line_ids.is_ma", "line_ids.is_investment")
    def _compute_flag_line_ids(self):
        for record in self:
            record.recurrent_line_ids = record.line_ids.filtered("is_recurrent")
            record.ma_line_ids = record.line_ids.filtered("is_ma")
            record.investment_line_ids = record.line_ids.filtered("is_investment")

    # ชดใช้เงินคงคลัง
    TREASURY_REPLENISHMENT_CODES = ["0702000001", "5108000038"]
    DEDUCTED_RESERVE_CODES = ["0702000002", "0702000003"]

    @api.depends("line_ids.code", "line_ids.balance", "line_ids.is_recurrent", "line_ids.is_ma", "line_ids.is_investment")
    def _compute_totals(self):
        for record in self:
            line_ids = record.line_ids
            record.treasury_replenishment_amount = sum(
                line_ids.filtered(
                    lambda x: x.account_id.code in self.TREASURY_REPLENISHMENT_CODES
                ).mapped("balance")
            )
            record.deducted_reserve_amount = sum(
                line_ids.filtered(
                    lambda x: x.account_id.code in self.DEDUCTED_RESERVE_CODES
                ).mapped("balance")
            )
            record.maintenance_amount = sum(
                line_ids.filtered(lambda x: x.is_ma).mapped("balance")
            )
            record.capital_budget_amount = sum(
                line_ids.filtered(lambda x: x.is_investment).mapped("balance")
            )
            record.recurrent_budget_amount = sum(
                line_ids.filtered(lambda x: x.is_recurrent).mapped("balance")
            )
            record.code_0702000002 = sum(
                line_ids.filtered(lambda x: x.account_id.code in ["0702000002"]).mapped(
                    "balance"
                )
            )
            record.code_0702000003 = sum(
                line_ids.filtered(lambda x: x.account_id.code in ["0702000003"]).mapped(
                    "balance"
                )
            )
            record.external_funding_amount = 0
