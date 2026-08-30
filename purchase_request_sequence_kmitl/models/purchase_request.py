# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # Untranslated placeholder, like account.move's "/": the number is minted
    # later (at the state transition out of draft), so this value sits in the
    # DB and is read back by users in other locales. Anything translated here
    # (e.g. _("New")) would compare unequal to _() evaluated in the reader's
    # language — a th_TH draft storing "รายการใหม่" would look already-numbered
    # to an en_US user, skipping the mint. The friendly "New" label is
    # rendered by the form view instead.
    name = fields.Char(default="/")

    # True once the PR number has been minted — the fiscal year is then frozen
    # (it drives the number's year), even after a Reset to Draft.
    fiscal_year_locked = fields.Boolean(compute="_compute_fiscal_year_locked")

    # States a draft can move to that mean the request was dropped, not
    # submitted — no number should be spent (the sequence is no_gap). Modules
    # adding further such terminal states can extend this.
    _NO_NUMBER_STATES = ("draft", "cancelled")

    @api.model
    def _get_default_name(self):
        # Bypass the base's next_by_code("purchase.request") so records keep
        # the "/" placeholder until the state leaves draft and draws our
        # KMITL-format number below.
        return "/"

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
        number = (
            self.env["ir.sequence"]
            .with_context(ir_sequence_date=fiscal_date)
            .next_by_code("purchase.request.kmitl", sequence_date=fiscal_date)
        )
        if not number:
            # next_by_code returns False when this ir.sequence code doesn't
            # exist, meaning data/sequence.xml hasn't been loaded yet — letting
            # this through would silently leave the document unnumbered.
            raise UserError(
                _(
                    "Document number sequence (purchase.request.kmitl) not "
                    "found. Please upgrade the module."
                )
            )
        self.name = number

    @api.depends("name")
    def _compute_fiscal_year_locked(self):
        # "/" is the placeholder a request carries until the state leaves
        # draft and mints its number. Kept untranslated on purpose — see the
        # ``name`` field.
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
        res = super().write(vals)
        # Mint the document number on any transition out of draft, no matter
        # which button (or server-side write) triggers it — button_to_verify
        # is only one of several exits from draft (base's button_to_approve,
        # purchase_request_verify_state's to_examine path, ...), so hooking
        # a single button leaves the others with a dangling "/" name.
        if vals.get("state"):
            for record in self:
                if record.state not in self._NO_NUMBER_STATES:
                    record._assign_document_number()
        return res
