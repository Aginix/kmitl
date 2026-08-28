# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    _STATES = [("to_verify", "To be verified"), ("to_submit",)]

    is_purchase_request = fields.Boolean(compute="_compute_is_purchase_request")
    state = fields.Selection(
        selection_add=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        ondelete={
            "to_verify": "set default",
        },
    )
    can_request = fields.Boolean(compute="_compute_can_request")
    # True once the PR number has been minted — the fiscal year is then frozen
    # (it drives the number's year), even after a Reset to Draft.
    fiscal_year_locked = fields.Boolean(compute="_compute_fiscal_year_locked")

    def _compute_is_purchase_request(self):
        for rec in self:
            rec.is_purchase_request = rec._name == "purchase.request"

    def button_to_verify(self):
        self.ensure_one()
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        self.write({"state": "to_verify"})
        self._assign_document_number()

    def _assign_document_number(self):
        # The number's year must come from the ปีงบประมาณ, not today. In the
        # use_date_range path %(year_be)s reads the effective date from the
        # ``ir_sequence_date`` context (the date_range only drives the per-year
        # counter reset), so pin both to the fiscal year's end date — its
        # Gregorian year + 543 is the BE fiscal-year number (e.g. FY 2569 ends
        # 2026 → 2569).
        self.ensure_one()
        placeholders = {"New", _("New")}
        if self.name and self.name not in placeholders:
            return
        if not self.account_fiscal_year_id:
            raise ValidationError(
                _("Fiscal Year is required to generate the document number.")
            )
        fiscal_date = self.account_fiscal_year_id.date_to
        self.name = (
            self.env["ir.sequence"]
            .with_context(ir_sequence_date=fiscal_date)
            .next_by_code("purchase.request.kmitl", sequence_date=fiscal_date)
        ) or _("New")

    @api.depends("name")
    def _compute_fiscal_year_locked(self):
        placeholders = {"New", _("New")}
        for rec in self:
            rec.fiscal_year_locked = bool(
                rec.name and rec.name not in placeholders
            )

    def write(self, vals):
        # Freeze the fiscal year once the PR number has been assigned. The
        # number's year is derived from the fiscal year, so allowing FY changes
        # after minting would make the number inconsistent.
        if "account_fiscal_year_id" in vals:
            placeholders = {"New", _("New")}
            numbered = self.filtered(
                lambda r: r.name and r.name not in placeholders
            )
            if numbered:
                raise UserError(
                    _(
                        "The fiscal year is frozen once the PR number has been "
                        "assigned — changing it would make the number inconsistent."
                    )
                )
        return super().write(vals)

    @api.depends("state")
    def _compute_is_editable(self):
        super()._compute_is_editable()
        editable_states = ("draft", "to_verify", "to_submit", "returned")
        for record in self:
            record.is_editable = record.state in editable_states

    @api.depends("requested_by")
    def _compute_can_request(self):
        current_user = self.env.user
        is_manager = current_user.has_group(
            "purchase_request.group_purchase_request_manager"
        )
        is_admin = current_user.has_group("base.group_erp_manager")
        for rec in self:
            own_by_me = rec.requested_by.id == current_user.id
            rec.can_request = own_by_me or is_manager or is_admin

    def _compute_hide_reserve_budget_button(self):
        super()._compute_hide_reserve_budget_button()
        for rec in self:
            if rec.state == "to_verify":
                rec.hide_reserve_budget_button = False

    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        can_edit = self.env.user.has_group("budget.group_budget_commitment")
        for rec in self:
            if rec.state == "to_verify" and can_edit:
                rec.is_budget_editable = True
            elif rec.state == "to_submit":
                rec.is_budget_editable = False
