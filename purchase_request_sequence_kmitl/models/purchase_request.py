# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    name = fields.Char(
        string="Request Reference",
        compute="_compute_name",
        store=True,
        readonly=False,
        copy=False,
        tracking=True,
        default=lambda self: _("New"),
    )
    fiscal_year_locked = fields.Boolean(compute="_compute_fiscal_year_locked")

    _NAME_PLACEHOLDER_STATES = ("draft", "cancelled", "rejected")

    @api.model
    def _get_default_name(self):
        return _("New")

    @api.depends("state", "account_fiscal_year_id")
    def _compute_name(self):
        # The number's year must come from the ปีงบประมาณ, not today. In the
        # use_date_range path %(year_be)s reads the effective date from the
        # ``ir_sequence_date`` context (the date_range only drives the per-year
        # counter reset), so pin both to the fiscal year's end date — its
        # Gregorian year + 543 is the BE fiscal-year number (e.g. FY 2569 ends
        # 2026 → 2569).
        placeholders = {"New", _("New")}
        for record in self:
            if record.state in self._NAME_PLACEHOLDER_STATES:
                continue
            if record.name and record.name not in placeholders:
                continue
            if not record.account_fiscal_year_id:
                raise ValidationError(
                    _("Fiscal Year is required to generate the document number.")
                )
            fiscal_date = record.account_fiscal_year_id.date_to
            record.name = (
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
