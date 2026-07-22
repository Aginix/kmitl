# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "budget.commitment.mixin", "analytic.mixin"]

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
        domain=lambda self: self._domain_budget_account_id(),
        help="Budget account to be used for commitment",
        store=True,
        tracking=True,
        copy=True,
        readonly=False,
    )

    def _domain_budget_account_id(self):
        return [("purchase_ok", "=", True), ("product_id", "!=", False)]

    def _reservation_account_domain(self):
        # Only purchasable, product-backed budget codes are selectable for a PR,
        # matching the budget_account_id field domain — so the picker cannot
        # offer (nor apply_reservation_selection write) an account the PR would
        # reject or that would leave its lines product-less.
        return super()._reservation_account_domain() + self._domain_budget_account_id()

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    is_budget_editable = fields.Boolean(compute="_compute_is_budget_editable")

    hide_reserve_budget_button = fields.Boolean(
        compute="_compute_hide_reserve_budget_button"
    )

    product_id = fields.Many2one(related=False, readonly=False)

    @api.depends("state", "budget_commitment_id", "budget_commitment_id.state")
    def _compute_is_budget_editable(self):
        can_edit = self.env.user.has_group("budget.group_budget_commitment")
        for rec in self:
            if rec.state in ("to_verify", "to_approve") and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
            ):
                rec.is_budget_editable = can_edit
            else:
                rec.is_budget_editable = rec.is_editable

    @api.depends("state", "budget_commitment_id")
    def _compute_hide_reserve_budget_button(self):
        for rec in self:
            if rec.state in ("to_approve") and (
                rec.budget_commitment_id.state == "cancel"
                or not rec.budget_commitment_id
            ):
                rec.hide_reserve_budget_button = False
            else:
                rec.hide_reserve_budget_button = True

    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("sources")

    def button_draft(self):
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.write({"verified_by": "", "date_verified": False})
                    record.message_post(
                        body=_("Budget commitment %s has been cancelled")
                        % record.budget_commitment_id.name
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s")
                        % str(e)
                    )

        return super().button_draft()

    def action_view_budget_dashboard(self):
        self.ensure_one()
        root = self.budget_account_id
        while root.parent_id:
            root = root.parent_id
        return {
            "type": "ir.actions.client",
            "tag": "budget_dashboard",
            "name": "สถานะงบประมาณ",
            "target": "new",
            "context": {
                "default_fiscal_year_id": self.account_fiscal_year_id.id or False,
                "default_root_account_id": root.id if root else False,
                "default_department_analytic_id": self.department_analytic_id.id or False,
                "default_source_analytic_id": self.source_analytic_id.id or False,
                "default_fund_analytic_id": self.fund_analytic_id.id or False,
                "default_activity_analytic_id": self.activity_analytic_id.id or False,
            },
        }

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

    def _get_budget_commitment_extra_kwargs(self):
        """Extra kwargs forwarded to _create_budget_commitment().
        Override in bridge modules to inject e.g. operating_unit_id."""
        return {}

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()

        amount = sum(self.line_ids.mapped("estimated_cost"))

        # ปีงบยึดตามเอกสาร: check/reserve against this request's own fiscal year
        # (account_fiscal_year_id), not today() — otherwise a request whose FY differs
        # from today is checked against the wrong year.
        check_result = self._check_budget_availability(
            amount=amount,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
            account_fiscal_year_id=self.account_fiscal_year_id.id,
        )

        if not check_result["is_sufficient"]:
            raise UserError(
                _("Cannot reserve budget due to insufficient funds: %s")
                % check_result["message"]
            )

        try:
            commitment = self._create_budget_commitment(
                amount=amount,
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.name,
                description=f"Purchase Request: {self.name}",
                auto_reserve=True,
                account_fiscal_year_id=self.account_fiscal_year_id.id,
                **self._get_budget_commitment_extra_kwargs(),
            )
            self.message_post(
                body=_("Budget reserved: %s for amount %s") % (commitment.name, amount)
            )
            self.button_to_submit()
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.request",
                "view_mode": "form",
                "res_id": self.id,
                "target": "current",
                "context": self.env.context,
            }

        except UserError as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))

    def _compute_to_approve_allowed(self):
        super()._compute_to_approve_allowed()
        for rec in self:
            rec.to_approve_allowed = rec.state == "to_submit" and any(
                not line.cancelled and line.product_qty for line in rec.line_ids
            )

    def button_draft(self):
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.write({"verified_by": "", "date_verified": False})
                    record.message_post(
                        body=_("Budget commitment %s has been cancelled")
                        % record.budget_commitment_id.name
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s")
                        % str(e)
                    )

        return super().button_draft()

    def button_rejected(self):
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.message_post(
                        body=_("Budget commitment %s has been cancelled")
                        % record.budget_commitment_id.name
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s")
                        % str(e)
                    )

        return super().button_rejected()

    def button_cancel(self):
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.message_post(
                        body=_("Budget commitment %s has been cancelled")
                        % record.budget_commitment_id.name
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s")
                        % str(e)
                    )

        return super().button_cancel()

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic_distribution set analytic distribution on all order lines"""
        if self.analytic_distribution:
            self.line_ids.update({"analytic_distribution": self.analytic_distribution})

    def write(self, vals):
        result = super().write(vals)
        if "budget_account_id" in vals:
            for rec in self:
                product = rec.budget_account_id.product_id
                if product and rec.line_ids:
                    rec.line_ids.write({"product_id": product.id})
        return result

    @api.onchange("budget_account_id")
    def _onchange_budget_account_id(self):
        self._apply_budget_account_product()

    def _apply_budget_account_product(self):
        """Set the product from the budget account and ensure a PR line.

        Shared by the budget_account_id onchange and the reservation picker:
        the picker writes via ORM (no onchange fires), so it calls this directly
        to keep the PR line in sync with the chosen budget code.
        """
        product_id = self.budget_account_id.product_id
        if not product_id:
            return
        self.product_id = product_id.id
        if self.line_ids:
            self.line_ids.write({"product_id": product_id.id})
        else:
            default_price = self.env.context.get("default_price_unit", 0)
            self.line_ids = [
                Command.create(
                    {
                        "product_id": product_id.id,
                        "name": product_id.display_name,
                        "product_uom_id": product_id.uom_id.id,
                        "price_unit": getattr(self, "procurement_plan_id", False)
                        and self.procurement_plan_id.total_price
                        or default_price,
                        "product_qty": 1.0,
                    }
                )
            ]

    def apply_reservation_selection(self, selections, dims=None):
        """Picker write-back: set the budget code + dimensions, then sync the
        product line (the manual onchange does not fire on an ORM write)."""
        res = super().apply_reservation_selection(selections, dims=dims)
        self._apply_budget_account_product()
        return res
