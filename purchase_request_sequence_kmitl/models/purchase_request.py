# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    @api.model
    def _get_default_name(self):
        return _("New")

    def _assign_purchase_request_sequence(self):
        self.ensure_one()
        if self.name and re.match(r"^PR/\d{4}/\d+$", self.name):
            return
        fy = self.account_fiscal_year_id
        if not fy:
            raise ValidationError(_("Fiscal year is required."))
        match = re.search(r"\d{4}", fy.name or "")
        if not match:
            raise ValidationError(
                _("Fiscal year name %s must contain a 4-digit year.") % fy.name
            )
        fiscal_year = match.group(0)
        seq_code = f"purchase.request.{fiscal_year}"
        Sequence = self.env["ir.sequence"].sudo()
        if not Sequence.search([("code", "=", seq_code)], limit=1):
            Sequence.create(
                {
                    "name": f"Purchase Request {fiscal_year}",
                    "code": seq_code,
                    "prefix": f"PR/{fiscal_year}/",
                    "padding": 4,
                    "number_increment": 1,
                }
            )
        self.name = Sequence.next_by_code(seq_code)

    def button_to_verify(self):
        for rec in self:
            rec._assign_purchase_request_sequence()
        return super().button_to_verify()
