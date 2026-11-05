from odoo import _, api, fields, models
from odoo.tools.misc import formatLang


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    amount_tax_manual = fields.Monetary(
        string="Manual VAT",
        copy=False,
        tracking=True,
        help="VAT amount edited manually by the user. "
        "Empty means the computed VAT is used.",
    )

    def _has_manual_tax(self):
        self.ensure_one()
        return bool(self.amount_tax_manual and self.tax_id)

    def _get_computed_amount_tax(self):
        """VAT computed from the lines, ignoring any manual amount."""
        self.ensure_one()
        if self.company_id.tax_calculation_rounding_method == "round_globally":
            totals = self.env["account.tax"]._compute_taxes(
                [line._convert_to_tax_base_line_dict() for line in self.line_ids]
            )["totals"]
            return totals.get(self.currency_id, {}).get("amount_tax", 0.0)
        return sum(self.line_ids.mapped("price_tax"))

    @api.depends("line_ids.price_total", "amount_tax_manual")
    def _amount_all(self):
        res = super()._amount_all()
        for record in self.filtered(lambda r: r._has_manual_tax()):
            record.amount_tax = record.amount_tax_manual
            record.amount_total = record.amount_untaxed + record.amount_tax
        return res

    @api.depends_context("lang")
    @api.depends(
        "line_ids.tax_id",
        "line_ids.price_subtotal",
        "amount_total",
        "amount_untaxed",
        "amount_tax_manual",
    )
    def _compute_tax_totals(self):
        res = super()._compute_tax_totals()
        for record in self.filtered(lambda r: r._has_manual_tax()):
            tax_totals = record.tax_totals
            groups = [g for gs in tax_totals["groups_by_subtotal"].values() for g in gs]
            if not groups:
                continue
            currency = record.currency_id or record.company_id.currency_id
            groups[0]["tax_group_amount"] = record.amount_tax_manual
            groups[0]["formatted_tax_group_amount"] = formatLang(
                self.env, record.amount_tax_manual, currency_obj=currency
            )
            tax_totals["amount_total"] = record.amount_total
            tax_totals["formatted_amount_total"] = formatLang(
                self.env, record.amount_total, currency_obj=currency
            )
            record.tax_totals = tax_totals
        return res

    @api.onchange("line_ids", "tax_id")
    def _onchange_reset_amount_tax_manual(self):
        # Lines or tax changed: go back to the computed VAT
        self.amount_tax_manual = 0.0

    def action_open_vat_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Edit VAT"),
            "res_model": "purchase.request.vat.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }
