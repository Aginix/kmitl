# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError, ValidationError


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    def action_reserve(self):
        # Mint the KMITL BC/<year_be>/NNNN number before super so its own mint
        # block (gated on name == _("New")) becomes a no-op. Pin both
        # ir_sequence_date (drives %(year_be)s) and sequence_date (drives the
        # ir.sequence.date_range bucket) to the fiscal year's date_to so the
        # year token and per-FY counter agree even when reserving on the
        # boundary day.
        for record in self:
            if record.state != "draft" or record.name != _("New"):
                continue
            if not record.account_fiscal_year_id:
                raise ValidationError(
                    _("Fiscal Year is required to generate the commitment number.")
                )
            fiscal_date = record.account_fiscal_year_id.date_to
            number = (
                self.env["ir.sequence"]
                .with_context(ir_sequence_date=fiscal_date)
                .next_by_code(
                    "budget.commitment.kmitl", sequence_date=fiscal_date,
                )
            )
            if not number:
                raise UserError(
                    _(
                        "Document number sequence (budget.commitment.kmitl) "
                        "not found. Please upgrade the module."
                    )
                )
            record.name = number
        return super().action_reserve()
