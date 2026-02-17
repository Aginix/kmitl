# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

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

    TREASURY_REPLENISHMENT_CODES = ["0702000001"]
    DEDUCTED_RESERVE_CODES = ["0702000002", "0702000003"]

    # งบลงทุน
    CAPITAL_BUDGET_CODES = [
        "5411000001",
        "5411000002",
        "5411000003",
        "5411000009",
        "5104030207",
        "5104030208",
        "5104030209",
    ]

    # ค่าดูแลและบำรุงรักษา
    MAINTENANCE_CODES = ["5104010204", "5104010205", "5104010206"]

    # งบประจำ
    RECURRENT_BUDGET_CODES = ["5104010203"]

    @api.depends("line_ids.code", "line_ids.balance")
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
                line_ids.filtered(
                    lambda x: x.account_id.code in self.MAINTENANCE_CODES
                ).mapped("balance")
            )
            record.capital_budget_amount = sum(
                line_ids.filtered(
                    lambda x: x.account_id.code in self.CAPITAL_BUDGET_CODES
                ).mapped("balance")
            )
            record.recurrent_budget_amount = sum(
                line_ids.filtered(
                    lambda x: x.account_id.code in self.RECURRENT_BUDGET_CODES
                ).mapped("balance")
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
