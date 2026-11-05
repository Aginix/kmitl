from odoo import api, fields, models

from .tax_adjustment import apply_tax_adjustment


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    amount_tax_adjustment = fields.Monetary(
        string="VAT Adjustment",
        copy=False,
        readonly=True,
        tracking=True,
        help="Difference between the VAT edited on the purchase request "
        "and the computed VAT. Carried to the disbursement request.",
    )

    @api.depends("line_ids.price_total", "amount_tax_adjustment")
    def _amount_all(self):
        res = super()._amount_all()
        for record in self.filtered(lambda r: r.tax_id and r.amount_tax_adjustment):
            record.amount_tax += record.amount_tax_adjustment
            record.amount_total = record.amount_untaxed + record.amount_tax
            record.estimated_cost = record.amount_total
        return res

    @api.depends_context("lang")
    @api.depends(
        "line_ids.tax_id",
        "line_ids.price_subtotal",
        "amount_total",
        "amount_untaxed",
        "amount_tax_adjustment",
    )
    def _compute_tax_totals(self):
        res = super()._compute_tax_totals()
        for record in self.filtered(lambda r: r.tax_id and r.amount_tax_adjustment):
            record.tax_totals = apply_tax_adjustment(
                self.env,
                record.tax_totals,
                record.amount_tax_adjustment,
                record.amount_total,
                record.currency_id or record.company_id.currency_id,
            )
        return res

    @api.onchange("line_ids", "tax_id")
    def _onchange_reset_amount_tax_adjustment(self):
        # Lines or tax changed: go back to the computed VAT
        self.amount_tax_adjustment = 0.0

    def _prepare_disbursement_request_vals(self):
        vals = super()._prepare_disbursement_request_vals()
        if self.tax_id:
            vals["amount_tax_adjustment"] = self.amount_tax_adjustment
        return vals
