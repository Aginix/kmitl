# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
        compute="_compute_budget_account_id",
        domain=[("purchase_ok", "=", True), ("product_id", "!=", False)],
        help="Budget account to be used for commitment",
        store=True,
        tracking=True,
        readonly=False,
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        readonly=False,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
        readonly=False,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
        readonly=False,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
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

    @api.depends("state")
    def _compute_is_budget_editable(self):
        can_edit = (
            self.env.user.has_group("budget.group_budget_commitment")
            or self.env.user.has_group(
                "purchase_request.group_purchase_request_manager"
            )
            or self.env.user.has_group("base.group_erp_manager")
        )
        for rec in self:
            if rec.state in ("to_approve") and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
            ):
                rec.is_budget_editable = can_edit
            else:
                rec.is_budget_editable = rec.is_editable

    @api.depends("state", "budget_commitment_id")
    def _compute_hide_reserve_budget_button(self):
        can_edit = (
            self.env.user.has_group("budget.group_budget_commitment")
            or self.env.user.has_group(
                "purchase_request.group_purchase_request_manager"
            )
            or self.env.user.has_group("base.group_erp_manager")
        )
        for rec in self:
            if rec.state in ("to_approve") and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
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

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()

        amount = sum(self.line_ids.mapped("estimated_cost"))

        check_result = self._check_budget_availability(
            amount=amount,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
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
            )
            self.message_post(
                body=_("Budget reserved: %s for amount %s") % (commitment.name, amount)
            )
            self.state = "to_approve"
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

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic_distribution set analytic distribution on all order lines"""
        if self.analytic_distribution:
            self.line_ids.update({"analytic_distribution": self.analytic_distribution})

    @api.onchange("budget_account_id")
    def _onchange_product_id_create_line(self):
        product_id = self.budget_account_id.product_id
        if not product_id:
            return

        if self.line_ids:
            for line in self.line_ids:
                line.product_id = product_id
        else:
            self.line_ids = [
                Command.create(
                    {
                        "product_id": product_id,
                        "name": product_id.display_name,
                        "product_uom_id": product_id.uom_id.id,
                        "product_qty": 1.0,
                    }
                )
            ]
