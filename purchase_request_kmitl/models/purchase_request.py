# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # ── FIELDS ───────────────────────────────────────────────────────────────

    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    purchase_type_id = fields.Many2one(
        comodel_name="purchase.type",
        string="Purchase Type",
        ondelete="restrict",
        index=True,
        domain=lambda self: self._get_domain_purchase_type(),
        default=lambda self: self.env["purchase.type"].search(
            [("is_default", "=", True)], limit=1
        ),
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
    to_create = fields.Selection(
        related="purchase_type_id.to_create",
    )
    procurement_method_ids = fields.Many2many(
        related="purchase_type_id.procurement_method_ids",
    )
    expense_reason = fields.Text(
        string="Reason",
    )
    procurement_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Procurement Committees",
        domain=[("committee_type", "=", "procurement")],
        copy=True,
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Acceptance Committees",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
        tracking=True,
    )
    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
    )
    verified_by = fields.Many2one(
        comodel_name="res.users",
        string="Confirmed By",
        index=True,
        copy=False,
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    date_verified = fields.Date(
        string="Confirmed Date",
        copy=False,
    )
    date_approved = fields.Date(
        string="Approved Date",
        copy=False,
    )

    is_construction = fields.Boolean(string="Construction", readonly=True)

    title = fields.Char(string="title", tracking=True)

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        readonly=False,
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        tracking=True,
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        copy=False,
        default=lambda self: self.env.user,
        index=True,
    )

    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="TOR Committees",
        domain=[("committee_type", "=", "tor_committee")],
        copy=True,
    )

    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Price Determine Committees",
        domain=[("committee_type", "=", "price_determine")],
        copy=True,
    )

    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Evaluation Committees",
        domain=[("committee_type", "=", "evaluation")],
        copy=True,
    )

    work_supervisor_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Supervisors",
        domain=[("committee_type", "=", "work_supervisor")],
        copy=True,
    )

    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")

    # New state selection — single source of truth (replaces OCA base + module overrides)
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("reserve_budget", "รอจองงบประมาณ"),
            ("confirm", "รอผู้ขอยืนยัน"),
            ("to_submit", "รอส่งเรื่องอนุมัติให้จัดหา"),
            ("to_approve", "รออนุมัติให้จัดหา"),
            ("egp", "รอดำเนินการ e-GP"),
            ("approved", "อนุมัติให้จัดหา"),
            ("in_pa", "อยู่ระหว่างจัดหา"),
            ("purchasing", "อยู่ระหว่างจัดซื้อจัดจ้าง"),
            ("done", "จัดซื้อจัดจ้างเสร็จสิ้น"),
            ("cancel", "ยกเลิก"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        required=True,
        copy=False,
        index=True,
        ondelete={
            # Map obsolete values from old selection (pre-migration handles data; this is a safety net)
            "in_progress": "set default",
            "rejected": "set default",
            "to_examine": "set default",
            "to_verify": "set default",
        },
    )

    # ── COMPUTES ─────────────────────────────────────────────────────────────

    @api.depends("state", "purchase_count")
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = (
                rec.state != "purchasing" or rec.purchase_count > 0
            )

    # ── HELPERS ──────────────────────────────────────────────────────────────

    def _get_domain_purchase_type(self):
        return [("visible_on_purchase_request", "=", True)]

    def get_estimated_cost_currency(self, date=False):
        """Get estimated cost with currency"""
        self.ensure_one()
        date = date or fields.Date.context_today(self)
        estimated_cost = sum(self.line_ids.mapped("estimated_cost"))
        if self.currency_id != self.company_id.currency_id:
            if hasattr(self, "manual_currency") and self.manual_currency:
                rate = (
                    self.custom_rate
                    if self.type_currency == "inverse_company_rate"
                    else (1.0 / self.custom_rate)
                )
                estimated_cost = estimated_cost * rate
            else:
                estimated_cost = self.currency_id._convert(
                    estimated_cost, self.company_id.currency_id, self.company_id, date
                )
        return estimated_cost

    def _check_pr_exceptions(self):
        """Pre-check exceptions before confirming data. Override in bridge modules to add checks."""
        self.ensure_one()
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return False

    # ── TRANSITIONS ──────────────────────────────────────────────────────────

    def button_send_reserve_budget(self):
        """draft → reserve_budget  (triggered by assigned_to / พัสดุ)"""
        for rec in self:
            rec.write({"state": "reserve_budget"})

    def button_pullback_to_draft(self):
        """confirm → draft  (triggered by ผู้ขอ — releases budget commitment)"""
        return self.button_draft()

    def button_return_to_draft(self):
        """to_submit → draft  (triggered by พัสดุ — releases budget commitment)"""
        return self.button_draft()

    def button_confirm_data(self):
        """confirm → to_submit  (triggered by ผู้ขอ — sets verified_by, checks exceptions)"""
        self.ensure_one()
        popup = self._check_pr_exceptions()
        if popup:
            return popup
        self.write(
            {
                "state": "to_submit",
                "verified_by": self.env.user.id,
                "date_verified": fields.Date.context_today(self),
            }
        )

    def button_cancel_confirm(self):
        """confirm → cancel  (triggered by ผู้ขอ — releases budget commitment)"""
        return self.button_rejected()

    def _on_pa_approved(self):
        """in_pa → purchasing  (called by PA sarabun completion callback)"""
        self.ensure_one()
        if self.state == "in_pa":
            self.write({"state": "purchasing"})

    def _on_pa_rejected_or_deleted(self):
        """in_pa → approved  (called when PA is rejected or deleted, budget kept)"""
        self.ensure_one()
        if self.state == "in_pa":
            self.write({"state": "approved"})

    # ── OCA METHOD OVERRIDES ──────────────────────────────────────────────────

    def button_rejected(self):
        """Override OCA button_rejected: map rejection to 'cancel' in new state machine.
        Budget commitment cancellation is handled by purchase_request_budget's super() chain
        before this method is reached. We intercept here and write 'cancel' instead of 'rejected'."""
        self.write({"state": "cancel"})
        return True

    def button_approved(self):
        """Set approved_by and date_approved, then advance to approved state."""
        self.write(
            {
                "approved_by": self.env.user.id,
                "date_approved": fields.Date.context_today(self),
            }
        )
        return super().button_approved()

    def button_in_progress(self):
        """'in_progress' is gone: any PO creation now maps directly to 'done'.
        Called by OCA's make_purchase_order wizard for partial PO coverage."""
        self.write({"state": "done"})
        return True

    # ── ONCHANGES ─────────────────────────────────────────────────────────────

    @api.onchange("purchase_type_id")
    def _onchange_purchase_type_id(self):
        procurement_methods = self.purchase_type_id.procurement_method_ids
        self.update(
            {
                "procurement_method_id": len(procurement_methods) == 1
                and procurement_methods.id
                or False,
            }
        )
