# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model_create_multi
    def create(self, vals_list):
        Sequence = self.env["ir.sequence"]
        FiscalYear = self.env["account.fiscal.year"]
        for vals in vals_list:
            if vals.get("name") and vals["name"] != _("New"):
                continue
            fy = FiscalYear.browse(vals.get("account_fiscal_year_id"))
            if not fy:
                raise ValidationError(
                    _("Fiscal Year is required to generate the PO number.")
                )
            # Pin sequence_date/ir_sequence_date to the FY's end date so
            # %(year_be)s in the prefix resolves to the fiscal year's BE year
            # (Gregorian year of date_to + 543), not today's.
            fiscal_date = fy.date_to
            number = (
                Sequence
                .with_context(ir_sequence_date=fiscal_date)
                .next_by_code("purchase.order.kmitl", sequence_date=fiscal_date)
            )
            if not number:
                raise UserError(
                    _(
                        "Document number sequence (purchase.order.kmitl) not "
                        "found. Please upgrade the module."
                    )
                )
            vals["name"] = number
        return super().create(vals_list)
