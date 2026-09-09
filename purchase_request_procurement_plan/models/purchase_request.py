# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    use_procurement_plan = fields.Boolean(
        string="Use Procurement Plan",
        store=True,
    )

    budget_selection_mode = fields.Selection(
        selection_add=[("procurement_plan", "แผนจัดซื้อจัดจ้าง")],
        ondelete={"procurement_plan": "set default"},
    )

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan",
        string="Procurement Plan",
        domain="",
        tracking=True,
    )

    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        compute="_compute_analytic_id",
        inverse="_inverse_procurement_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
        "procurement_plan": "procurement_plan_analytic_id",
    }

    def _domain_budget_account_id(self):
        return super()._domain_budget_account_id() + [("procurement_plan", "=", False)]

    def _reservation_commitment_mode_domain(self):
        domain = super()._reservation_commitment_mode_domain()
        if self.budget_selection_mode == "procurement_plan":
            domain = domain + [("account_id.procurement_plan", "=", True)]
        return domain

    def _check_drawable_commitment(self, commitment):
        # A plan's shared commitment sits on a ``procurement_plan`` budget code
        # this PR may not *reserve new* on (ADR-0006), so the base gate — which
        # mirrors the full reserve-new field domain — would reject it. Drawing it
        # down is allowed, but the code must still be a purchasable, product-backed
        # PR budget code just like a directly selected one: check it against the
        # base domain (purchase_ok + product), lifting only the ``procurement_plan``
        # exclusion.
        if commitment.procurement_plan_id:
            if not self.env["budget.account"].search_count(
                super()._domain_budget_account_id()
                + [("id", "=", commitment.account_id.id)]
            ):
                raise UserError(
                    _("รหัสงบประมาณของใบจองที่เลือกไม่สามารถใช้กับเอกสารนี้ได้")
                )
            return True
        return super()._check_drawable_commitment(commitment)

    def _inverse_procurement_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("procurement_plan")

    @api.depends("state", "use_procurement_plan", "procurement_plan_id")
    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        for rec in self:
            if rec.use_procurement_plan:
                rec.is_budget_editable = False

    @api.onchange("use_procurement_plan", "procurement_plan_id")
    def _onchange_procurement_plan_id(self):
        if self.use_procurement_plan:
            if self.procurement_plan_id:
                self.account_fiscal_year_id = self.procurement_plan_id.account_fiscal_year_id.id
                self.procurement_method_id = self.procurement_plan_id.procurement_method_id.id
                self.budget_account_id = self.procurement_plan_id.budget_account_id.id
                self.analytic_distribution = self.procurement_plan_id.analytic_distribution
                self.title = _("%s") % self.procurement_plan_id.description
        else:
            self.procurement_plan_id = False
            self.budget_account_id = False
            self.analytic_distribution = False

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

    def _prepare_commitment_vals(
        self,
        amount,
        activity_analytic_id,
        fund_analytic_id,
        department_analytic_id,
        source_analytic_id,
        ref,
        description,
        budget_account_id,
        include_company=True,
        **kwargs,
    ):
        commitment_vals = super()._prepare_commitment_vals(
            amount,
            activity_analytic_id,
            fund_analytic_id,
            department_analytic_id,
            source_analytic_id,
            ref,
            description,
            budget_account_id,
            include_company=include_company,
            **kwargs,
        )

        if kwargs.get("procurement_plan_id"):
            commitment_vals["procurement_plan_id"] = kwargs["procurement_plan_id"]

        return commitment_vals

    def action_reserve_budget(self):
        """Plan-driven PRs draw down the plan's shared commitment instead of
        creating their own (D2). Non-plan PRs keep the standard own-commitment
        behaviour (D4)."""
        self.ensure_one()
        if self.use_procurement_plan and self.procurement_plan_id:
            plan = self.procurement_plan_id
            commitment = plan.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            )[:1]
            if not commitment:
                raise UserError(
                    _(
                        "แผนจัดซื้อจัดจ้างยังไม่ได้จองงบประมาณ "
                        "(แผนต้องอยู่สถานะรอดำเนินการ)"
                    )
                )
            self.budget_commitment_id = commitment.id
            if plan.state == "verified":
                plan.action_in_progress()
            self.button_to_approve()
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.request",
                "view_mode": "form",
                "res_id": self.id,
                "target": "current",
                "context": self.env.context,
            }
        return super().action_reserve_budget()

    def _action_draw_from_reservation(self):
        """PR-first draw of a procurement plan's shared commitment (as opposed
        to the source-driven ``procurement.plan`` create-from-plan button
        above): derive the plan, enforce 1-แผน-1-ใบ, link it and copy its
        procurement method, advance the plan out of ``verified``, then run the
        base draw — which copies the commitment's dims/account/FY onto the PR
        + lines, validates via the already-overridden
        ``_check_drawable_commitment``, and advances state."""
        plan = self.reservation_commitment_id.procurement_plan_id
        if plan:
            self._check_one_active_pr(plan)
            self.write(
                {
                    "use_procurement_plan": True,
                    "procurement_plan_id": plan.id,
                    "procurement_method_id": plan.procurement_method_id.id,
                }
            )
            if plan.state == "verified":
                plan.action_in_progress()
        return super()._action_draw_from_reservation()

    def _cancel_budget_commitment(self):
        """Never cancel a shared plan commitment when a plan-driven PR is reset
        or rejected — just detach this PR from it (D3)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        if commitment and commitment.procurement_plan_id:
            self.budget_commitment_id = False
            return True
        return super()._cancel_budget_commitment()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered(lambda r: r.procurement_plan_id):
            record._link_to_procurement_plan()
        return records

    def _check_one_active_pr(self, plan):
        """Raise unless this PR is the plan's only active (non-rejected) PR
        (ADR-0006, 1 แผน ต่อ 1 ใบขอซื้อ). Shared by the source-driven
        create-from-plan link and the PR-first draw-down path."""
        active_others = plan.purchase_request_ids.filtered(
            lambda r: r.id != self.id and r.state != "rejected"
        )
        if active_others:
            raise UserError(
                _(
                    "แผนจัดซื้อจัดจ้าง %s มีใบขอซื้อที่ยังดำเนินการอยู่แล้ว "
                    "(1 แผน ต่อ 1 ใบขอซื้อ)"
                )
                % plan.display_name
            )

    def _link_to_procurement_plan(self):
        """A plan-driven PR (created from the plan, ADR-0006) enforces one active
        PR per plan, links the plan's already-reserved shared commitment, and
        starts the plan. Reservation itself happened at appropriation post."""
        self.ensure_one()
        plan = self.procurement_plan_id
        if not self.use_procurement_plan:
            self.use_procurement_plan = True
        self._check_one_active_pr(plan)
        if not self.budget_commitment_id:
            commitment = plan.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            )[:1]
            if commitment:
                self.budget_commitment_id = commitment.id
        if plan.state == "verified":
            plan.action_in_progress()

    def button_rejected(self):
        res = super().button_rejected()
        for record in self:
            record._reopen_plan_on_reject()
        return res

    def _reopen_plan_on_reject(self):
        """When the single plan-driven PR is rejected, return the plan to
        ``verified`` so a replacement PR can be created — but only while no draw-down
        has started and no other active PR exists (ADR-0006, decision ข)."""
        self.ensure_one()
        plan = self.procurement_plan_id
        if not plan or plan.state != "in_progress":
            return
        active_others = plan.purchase_request_ids.filtered(
            lambda r: r.id != self.id and r.state != "rejected"
        )
        consumed = any(c.total_consumed for c in plan.budget_commitment_ids)
        if active_others or consumed:
            return
        plan.write({"state": "verified"})
        plan.message_post(
            body=_("ใบขอซื้อ %s ถูกปฏิเสธ แผนกลับสู่สถานะรอดำเนินการ")
            % self.display_name
        )


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        required=False,
        tracking=True,
    )

    purchase_request_count = fields.Integer(
        string="Purchase Requests Count", compute="_compute_purchase_request_count"
    )

    @api.depends("purchase_request_ids")
    def _compute_purchase_request_count(self):
        for record in self:
            record.purchase_request_count = len(record.purchase_request_ids)

    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="procurement_plan_id",
        string="Purchase Requests",
    )

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = {
            "name": _("ใบขอซื้อ (พ.1)"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "domain": [("id", "in", self.purchase_request_ids.ids)],
        }
        # One plan normally holds a single PR — open it straight in form view.
        if len(self.purchase_request_ids) == 1:
            action.update(
                {"view_mode": "form", "res_id": self.purchase_request_ids.id}
            )
        else:
            action["view_mode"] = "tree,form"
        return action

    can_create_purchase_request = fields.Boolean(
        compute="_compute_can_create_purchase_request"
    )

    @api.depends("state", "purchase_request_ids.state")
    def _compute_can_create_purchase_request(self):
        """Show the create-PR button while the plan is verified (budget
        reserved) and has no active PR."""
        for rec in self:
            active = rec.purchase_request_ids.filtered(
                lambda r: r.state != "rejected"
            )
            rec.can_create_purchase_request = (
                rec.state == "verified" and not active
            )

    def action_create_purchase_request(self):
        """Create the plan's single purchase request (ADR-0006). Opens a PR form
        pre-filled from the plan via context defaults; the existing onchange
        builds the budget lines. The plan must be verified and hold an
        active reservation."""
        self.ensure_one()
        if self.state != "verified":
            raise UserError(
                _("สร้างใบขอซื้อได้เฉพาะแผนที่อยู่สถานะรอดำเนินการเท่านั้น")
            )
        if self.purchase_request_ids.filtered(lambda r: r.state != "rejected"):
            raise UserError(
                _("แผนนี้มีใบขอซื้อที่ยังดำเนินการอยู่แล้ว (1 แผน ต่อ 1 ใบขอซื้อ)")
            )
        commitment = self.budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        )[:1]
        if not commitment:
            raise UserError(
                _("แผนยังไม่ได้จองงบประมาณ ไม่สามารถสร้างใบขอซื้อได้")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("สร้างใบขอซื้อจากแผน"),
            "res_model": "purchase.request",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_use_procurement_plan": True,
                "default_budget_selection_mode": "procurement_plan",
                "default_procurement_plan_id": self.id,
                "default_budget_commitment_id": commitment.id,
                "default_budget_account_id": self.budget_account_id.id,
                "default_account_fiscal_year_id": self.account_fiscal_year_id.id,
                "default_procurement_method_id": self.procurement_method_id.id,
                "default_analytic_distribution": self.analytic_distribution,
                "default_title": self.description,
            },
        }
