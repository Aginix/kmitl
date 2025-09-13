# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "analytic.distribution.mixin"]

    READONLY_STATES = {
        "purchase": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        readonly=True,
        copy=False,
        help="Related budget commitment for this purchase request",
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        help="Budget account to be used for commitment",
    )

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan",
        string="รายการแผนจัดซื้อจัดจ้าง",
        tracking=True,
        inverse="_inverse_procurement_plan_id",
    )

    def _inverse_procurement_plan_id(self):
        for rec in self:
            if rec.procurement_plan_id:
                rec.budget_account_id = rec.procurement_plan_id.budget_account_id.id
                rec.activity_analytic_id = rec.procurement_plan_id.activity_analytic_id.id
                rec.department_analytic_id = rec.procurement_plan_id.department_analytic_id.id
                rec.fund_analytic_id = rec.procurement_plan_id.fund_analytic_id.id
                rec.source_analytic_id = rec.procurement_plan_id.source_analytic_id.id
                rec.procurement_plan_analytic_id = rec.procurement_plan_id.analytic_account_id.id
            else:
                rec.procurement_plan_id = False
                rec.budget_account_id = False
                rec.activity_analytic_id = False
                rec.department_analytic_id = False
                rec.fund_analytic_id = False
                rec.source_analytic_id = False
                rec.procurement_plan_analytic_id = False

    @api.onchange("procurement_plan_id")
    def _onchange_procurement_plan_id(self):
        if self.procurement_plan_id:
            self.budget_account_id = self.procurement_plan_id.budget_account_id.id
            self.activity_analytic_id = self.procurement_plan_id.activity_analytic_id.id
            self.department_analytic_id = self.procurement_plan_id.department_analytic_id.id
            self.fund_analytic_id = self.procurement_plan_id.fund_analytic_id.id
            self.source_analytic_id = self.procurement_plan_id.source_analytic_id.id
            self.procurement_plan_analytic_id = self.procurement_plan_id.analytic_account_id.id
        else:
            self.procurement_plan_id = False
            self.budget_account_id = False
            self.activity_analytic_id = False
            self.department_analytic_id = False
            self.fund_analytic_id = False
            self.source_analytic_id = False
            self.procurement_plan_analytic_id = False

    def action_open_budget_commitment(self):
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError("ยังไม่มี Budget Commitment สำหรับเอกสารนี้")

        return {
            "type": "ir.actions.act_window",
            "name": "Budget Commitment",
            "res_model": "budget.commitment",
            "view_mode": "form",
            "res_id": self.budget_commitment_id.id,
            "target": "current",
        }

    def action_view_procurement_plan(self):
        self.ensure_one()
        if not self.procurement_plan_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "type": "ir.actions.act_window",
            "res_model": "procurement.plan",
            "view_mode": "form",
            "res_id": self.procurement_plan_id.id,
            "target": "current",
        }

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic_distribution set analytic distribution on all order lines"""
        if self.analytic_distribution:
            self.order_line.update(
                {"analytic_distribution": self.analytic_distribution}
            )
        else:
            self.order_line.update(
                {"analytic_distribution": False}
            )

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        # vals["date_range_fy_id"] = purchase_request.date_range_fy_id.id
        vals["analytic_distribution"] = self.analytic_distribution
        vals["budget_commitment_id"] = self.budget_commitment_id.id
        vals["budget_account_id"] = self.budget_account_id.id
        vals["procurement_plan_analytic_id"] = self.procurement_plan_analytic_id.id
        return vals
