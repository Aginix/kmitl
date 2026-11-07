# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

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
        states=READONLY_STATES,
        copy=False,
        tracking=True,
        inverse="_inverse_budget_commitment_id",
        help="ใบจองงบประมาณที่ใบสั่งซื้อนี้หยิบไปใช้ — รหัสงบ/มิติ จะถูกคัดลอก"
        "จากใบจองแบบล็อก",
    )

    budget_commitment_domain = fields.Binary(
        compute="_compute_budget_commitment_domain",
        help="Record-aware domain for the budget commitment picker: a static "
        "field domain cannot see this order's own fiscal year.",
    )

    budget_account_product_id = fields.Many2one(
        related="budget_account_id.product_id",
        string="Budget Product",
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        states=READONLY_STATES,
        domain=lambda self: self._domain_budget_account_id(),
        help="Budget account to be used for commitment",
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

    def _domain_budget_commitment_id(self):
        """Reservations a standalone PO may draw: reserved/in-progress with
        obligable headroom, on a purchasable product-backed budget code, in this
        order's fiscal year."""
        return [
            ("state", "in", ("reserved", "partial")),
            ("available_to_obligate", ">", 0),
            ("account_id.purchase_ok", "=", True),
            ("account_id.product_id", "!=", False),
            ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
        ] + self._budget_commitment_mode_domain()

    def _budget_commitment_mode_domain(self):
        """Extension point for bridges to narrow the commitment picker."""
        return []

    @api.depends("account_fiscal_year_id")
    def _compute_budget_commitment_domain(self):
        for rec in self:
            rec.budget_commitment_domain = rec._domain_budget_commitment_id()

    @api.onchange("budget_commitment_id")
    def _onchange_budget_commitment_id(self):
        """Preview the picked commitment's budget code and dimensions on the
        live form; ``_inverse_budget_commitment_id`` writes them on save."""
        commitment = self.budget_commitment_id
        if not commitment:
            return
        self.budget_account_id = commitment.account_id.id
        self.activity_analytic_id = commitment.activity_analytic_id.id
        self.department_analytic_id = commitment.department_analytic_id.id
        self.fund_analytic_id = commitment.fund_analytic_id.id
        self.source_analytic_id = commitment.source_analytic_id.id
        self.procurement_plan_analytic_id = commitment.procurement_plan_analytic_id.id

    def _inverse_budget_commitment_id(self):
        """Copy the commitment's budget code and full dimension distribution
        onto the order and its lines server-side, so the locked budget fields
        always match the commitment drawn."""
        for rec in self.filtered("budget_commitment_id"):
            commitment = rec.budget_commitment_id
            rec.write(
                {
                    "budget_account_id": commitment.account_id.id,
                    "analytic_distribution": commitment.analytic_distribution or False,
                }
            )
            if rec.order_line and commitment.analytic_distribution:
                rec.order_line.write(
                    {"analytic_distribution": commitment.analytic_distribution}
                )

    @api.onchange("account_fiscal_year_id")
    def _onchange_account_fiscal_year_id_budget_commitment(self):
        if (
            self.budget_commitment_id
            and self.budget_commitment_id.account_fiscal_year_id
            != self.account_fiscal_year_id
        ):
            self.budget_commitment_id = False

    def _check_standalone_budget_commitment(self):
        """A PO raised without a purchase request draws its commitment directly:
        it must still be drawable and cover the order amount."""
        for rec in self.filtered(lambda r: r.budget_commitment_id and not r.request_id):
            commitment = rec.budget_commitment_id
            if commitment.state not in ("reserved", "partial"):
                raise UserError(
                    _("ใบจองงบประมาณ %s ไม่อยู่ในสถานะที่หยิบไปใช้ได้")
                    % commitment.display_name
                )
            if (
                float_compare(
                    rec.amount_total,
                    commitment.available_to_obligate,
                    precision_rounding=rec.currency_id.rounding,
                )
                > 0
            ):
                raise UserError(
                    _(
                        "ยอดใบสั่งซื้อ %(amount)s เกินงบคงเหลือของใบจองงบประมาณ "
                        "%(commitment)s (คงเหลือ %(available)s)"
                    )
                    % {
                        "amount": "{:,.2f}".format(rec.amount_total),
                        "commitment": commitment.display_name,
                        "available": "{:,.2f}".format(
                            commitment.available_to_obligate
                        ),
                    }
                )

    def button_confirm(self):
        self._check_standalone_budget_commitment()
        return super().button_confirm()

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
