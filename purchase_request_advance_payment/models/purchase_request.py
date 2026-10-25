from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # A loan is only ever created in the advance payment app, by picking this
    # request on it; the link is derived from the loans that point here.
    advance_payment_ids = fields.One2many(
        comodel_name="advance.payment",
        inverse_name="purchase_request_id",
        string="สัญญายืมเงินทั้งหมด",
    )
    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="สัญญายืมเงิน",
        compute="_compute_advance_payment_id",
        store=True,
        copy=False,
    )

    advance_payment_count = fields.Integer(
        compute="_compute_advance_payment_count",
    )

    @api.depends("advance_payment_ids.state")
    def _compute_advance_payment_id(self):
        """The request's live loan — at most one (see advance.payment's
        _check_one_loan_per_purchase_request)."""
        for rec in self:
            rec.advance_payment_id = rec.advance_payment_ids.filtered(
                lambda ap: ap.state != "cancel"
            )[:1]

    # Counted as the reader, not sudo: a PR approver or buyer who may not
    # read the loan gets no smart button instead of an AccessError behind it.
    @api.depends("advance_payment_id")
    @api.depends_context("uid")
    def _compute_advance_payment_count(self):
        AdvancePayment = self.env["advance.payment"]
        for rec in self:
            rec.advance_payment_count = (
                AdvancePayment.search_count([("id", "=", rec.advance_payment_id.id)])
                if rec.advance_payment_id
                else 0
            )

    def action_view_advance_payment(self):
        """Open the linked advance payment form."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "advance.payment",
            "res_id": self.advance_payment_id.id,
            "view_mode": "form",
            "target": "current",
        }
