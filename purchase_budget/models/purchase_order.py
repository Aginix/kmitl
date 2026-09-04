# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models
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

    def _domain_budget_account_id(self):
        return [("purchase_ok", "=", True), ("product_id", "!=", False)]

    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        domain=[("state", "not in", ["draft", "done", "cancel"])],
        states=READONLY_STATES,
        copy=False,
        help="Pick an existing budget commitment to consume; "
             "budget dimensions will be copied and locked from that commitment.",
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        states=READONLY_STATES,
        domain=lambda self: self._domain_budget_account_id(),
        help="Budget account to be used for commitment",
    )

    budget_account_product_id = fields.Many2one(
        related="budget_account_id.product_id",
        string="Budget Product",
        readonly=True,
    )

    activity_analytic_id = fields.Many2one(
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        states=READONLY_STATES,
    )

    use_procurement_plan = fields.Boolean(
        string="Use Procurement Plan", default=False
    )

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan",
        string="Procurement Plan",
        tracking=True,
        inverse="_inverse_procurement_plan_id",
    )

    def _inverse_procurement_plan_id(self):
        for rec in self:
            if rec.use_procurement_plan and rec.procurement_plan_id:
                rec.budget_account_id = rec.procurement_plan_id.budget_account_id.id
                rec.activity_analytic_id = rec.procurement_plan_id.activity_analytic_id.id
                rec.department_analytic_id = rec.procurement_plan_id.department_analytic_id.id
                rec.fund_analytic_id = rec.procurement_plan_id.fund_analytic_id.id
                rec.source_analytic_id = rec.procurement_plan_id.source_analytic_id.id
                rec.procurement_plan_analytic_id = rec.procurement_plan_id.analytic_account_id.id

    @api.onchange("use_procurement_plan", "procurement_plan_id")
    def _onchange_procurement_plan_id(self):
        if self.use_procurement_plan and self.procurement_plan_id:
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

    @api.onchange("budget_commitment_id")
    def _onchange_budget_commitment_id(self):
        for rec in self:
            if not rec.budget_commitment_id:
                continue
            budget = rec.budget_commitment_id
            rec.budget_account_id = budget.account_id
            rec.analytic_distribution = budget.analytic_distribution
            # Also mirror the individual dimension fields so the form shows
            # them immediately — the mixin's inverse only populates them on
            # save, which leaves those four rows blank until the record is
            # persisted.
            rec.activity_analytic_id = budget.activity_analytic_id
            rec.department_analytic_id = budget.department_analytic_id
            rec.fund_analytic_id = budget.fund_analytic_id
            rec.source_analytic_id = budget.source_analytic_id

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
        vals["analytic_distribution"] = self.analytic_distribution
        vals["budget_commitment_id"] = self.budget_commitment_id.id
        vals["budget_account_id"] = self.budget_account_id.id
        vals["procurement_plan_analytic_id"] = self.procurement_plan_analytic_id.id
        return vals

    @api.onchange("budget_account_id")
    def _onchange_budget_account_id(self):
        default_price = self.env.context.get("default_price_unit", 0)
        product = self.budget_account_id.product_id

        if not product:
            return

        self.product_id = product.id

        vals = {
            "product_id": product.id,
            "name": product.display_name,
            "price_unit": self.procurement_plan_id.total_price or default_price,
            "product_qty": 1.0,
            "product_uom": product.uom_id.id,
            "date_planned": fields.Datetime.now(),
        }

        if self.order_line:
            for line in self.order_line:
                line.update(vals)
        else:
            self.order_line = [Command.create(vals)]
