# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # Untranslated placeholder, like account.move's "/": the number is minted
    # later (at button_to_verify), so this value sits in the DB and is read back
    # by users in other locales. Anything translated here (e.g. _("New")) would
    # compare unequal to _() evaluated in the reader's language — a th_TH draft
    # storing "รายการใหม่" would look already-numbered to an en_US user, skipping
    # the mint. The friendly "New" label is rendered by the form view instead.
    name = fields.Char(default="/")

    # True once the PR number has been minted — the fiscal year is then frozen
    # (it drives the number's year), even after a Reset to Draft.
    fiscal_year_locked = fields.Boolean(compute="_compute_fiscal_year_locked")

    @api.model
    def _get_default_name(self):
        # Bypass the base's next_by_code("purchase.request") so records keep the
        # "/" placeholder until button_to_verify draws our KMITL-format number
        # below.
        return "/"

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
        if self.name and self.name != "/":
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
        ) or "/"

    @api.depends("name")
    def _compute_fiscal_year_locked(self):
        # "/" is the placeholder a request carries until button_to_verify mints
        # its number. Kept untranslated on purpose — see the ``name`` field.
        for record in self:
            record.fiscal_year_locked = bool(record.name and record.name != "/")

    def write(self, vals):
        # Freeze the fiscal year once the PR number has been assigned. The
        # number's year is derived from the fiscal year, so allowing FY changes
        # after minting would make the number inconsistent.
        if "account_fiscal_year_id" in vals:
            numbered = self.filtered(lambda r: r.name and r.name != "/")
            if numbered:
                raise UserError(
                    _(
                        "The fiscal year is frozen once the PR number has been "
                        "assigned — changing it would make the number inconsistent."
                    )
                )
        return super().write(vals)
