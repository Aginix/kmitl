from odoo import api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="Advance Payment",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.advance_payment_id:
                rec._create_usage_line()
        return records

    def unlink(self):
        usage_lines = self.env["advance.payment.usage.line"].search(
            [("disbursement_request_id", "in", self.ids)]
        )
        usage_lines.unlink()
        return super().unlink()

    @api.depends(
        "line_ids.price_subtotal",
        "line_ids.price_tax",
        "line_ids.price_total",
        "line_ids.amount_wht",
    )
    def _compute_amount_all(self):
        super()._compute_amount_all()
        for rec in self:
            if rec.advance_payment_id:
                rec._sync_usage_line_amount()

    def _create_usage_line(self):
        self.ensure_one()
        self.env["advance.payment.usage.line"].create(
            {
                "agreement_id": self.advance_payment_id.id,
                "disbursement_request_id": self.id,
                "amount": self.amount_total,
                "date": self.date or fields.Date.today(),
            }
        )

    def _sync_usage_line_amount(self):
        self.ensure_one()
        usage_line = self.env["advance.payment.usage.line"].search(
            [("disbursement_request_id", "=", self.id)], limit=1
        )
        if usage_line:
            usage_line.amount = self.amount_total
