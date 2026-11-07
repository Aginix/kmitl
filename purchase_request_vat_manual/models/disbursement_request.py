from odoo import api, fields, models

from .tax_adjustment import apply_tax_adjustment


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    amount_tax_adjustment = fields.Monetary(
        string="VAT Adjustment",
        copy=False,
        readonly=True,
        tracking=True,
        currency_field="currency_id",
        help="Difference between the VAT edited on the purchase request "
        "and the computed VAT. Applied to the vendor bill.",
    )

    def _has_tax_adjustment(self):
        self.ensure_one()
        return bool(self.amount_tax_adjustment and self.line_ids.tax_ids)

    @api.depends(
        "line_ids.price_subtotal",
        "line_ids.price_tax",
        "line_ids.price_total",
        "line_ids.amount_wht",
        "amount_tax_adjustment",
    )
    def _compute_amount_all(self):
        res = super()._compute_amount_all()
        for request in self.filtered(lambda r: r._has_tax_adjustment()):
            adjustment = request.amount_tax_adjustment
            request.amount_tax += adjustment
            request.amount_total += adjustment
            request.amount_net += adjustment
        return res

    @api.depends_context("lang")
    @api.depends(
        "line_ids.tax_ids",
        "line_ids.price_subtotal",
        "amount_total",
        "amount_untaxed",
        "amount_tax_adjustment",
    )
    def _compute_tax_totals(self):
        res = super()._compute_tax_totals()
        for request in self.filtered(lambda r: r._has_tax_adjustment()):
            request.tax_totals = apply_tax_adjustment(
                self.env,
                request.tax_totals,
                request.amount_tax_adjustment,
                request.amount_total,
                request.currency_id,
            )
        return res

    @api.onchange("line_ids")
    def _onchange_reset_amount_tax_adjustment(self):
        # Lines changed: go back to the computed VAT
        self.amount_tax_adjustment = 0.0

    def _create_bills(self):
        bills = super()._create_bills()
        if not self._has_tax_adjustment():
            return bills
        bill = bills.filtered(lambda b: b.line_ids.filtered("tax_line_id"))[:1]
        if bill:
            bill.tax_totals = apply_tax_adjustment(
                self.env,
                dict(bill.tax_totals),
                self.amount_tax_adjustment,
                bill.tax_totals["amount_total"] + self.amount_tax_adjustment,
                bill.currency_id,
            )
        return bills
