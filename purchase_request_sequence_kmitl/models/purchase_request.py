# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # True once the PR number has been minted — the fiscal year is then frozen
    # (it drives the number's year), even after a Reset to Draft.
    fiscal_year_locked = fields.Boolean(compute="_compute_fiscal_year_locked")

    @api.model
    def _get_default_name(self):
        # Bypass the base's next_by_code("purchase.request") so records keep the
        # _("New") placeholder until button_to_verify draws our KMITL-format
        # number below.
        return _("New")

    def button_to_verify(self):
        # Hook the mint into the workflow's canonical submission point.
        # ``super()`` runs the exception check and, on success, moves the state
        # out of ``draft``; if it returns the exception popup instead, state
        # stays at ``draft`` and the ``state != "draft"`` guard below skips the
        # mint so no number is wasted.
        res = super().button_to_verify()
        for record in self:
            if record.state != "draft":
                record._assign_document_number()
        return res

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
        for record in self:
            record.fiscal_year_locked = bool(
                record.name and record.name not in placeholders
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
