# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model_create_multi
    def create(self, vals_list):
        Sequence = self.env["ir.sequence"]
        FiscalYear = self.env["account.fiscal.year"]
        for vals in vals_list:
            if vals.get("name", "New") != "New":
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

    def write(self, vals):
        # The number embeds the ปีงบประมาณ (%(year_be)s of the FY's date_to) and
        # is minted in create(), so every saved PO is already numbered: changing
        # the fiscal year afterwards would desync PO/<year>/#### from the year
        # the money is actually spent under. The form keeps the field editable
        # while the record is new (see views/purchase_order_views.xml); this
        # guard closes the ORM/RPC path. Only an actual change is refused, so
        # bridges that re-write the field with its current value keep working.
        if "account_fiscal_year_id" in vals:
            changed = self.filtered(
                lambda o: o.account_fiscal_year_id.id != vals["account_fiscal_year_id"]
            )
            if changed:
                raise UserError(
                    _(
                        "The fiscal year is frozen once the PO number has been "
                        "assigned — changing it would make the number inconsistent."
                    )
                )
        return super().write(vals)
