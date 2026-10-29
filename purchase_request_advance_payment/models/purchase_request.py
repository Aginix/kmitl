from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    # A loan is only ever created in the advance payment app, by naming this
    # request on it, and several borrowers may draw on one request; the
    # request itself never waits on them (advance_payment ADR-0029).
    advance_payment_ids = fields.One2many(
        comodel_name="advance.payment",
        inverse_name="purchase_request_id",
        string="สัญญายืมเงินทั้งหมด",
    )

    advance_payment_count = fields.Integer(
        compute="_compute_advance_payment_count",
    )

    # Counted as the reader, not sudo: a PR approver or buyer who may not
    # read the loans gets no smart button instead of an AccessError behind it.
    @api.depends("advance_payment_ids")
    @api.depends_context("uid")
    def _compute_advance_payment_count(self):
        AdvancePayment = self.env["advance.payment"]
        can_read = AdvancePayment.check_access_rights("read", raise_exception=False)
        for rec in self:
            rec.advance_payment_count = (
                AdvancePayment.search_count(
                    [("purchase_request_id", "=", rec.id), ("state", "!=", "cancel")]
                )
                if can_read and isinstance(rec.id, int)
                else 0
            )

    def action_view_advance_payment(self):
        """Open the loans drawn against this request."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("สัญญายืมเงิน"),
            "res_model": "advance.payment",
            "view_mode": "tree,form",
            "domain": [("purchase_request_id", "=", self.id)],
            "target": "current",
        }
