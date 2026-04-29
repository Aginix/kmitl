from odoo import api, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    @api.depends("state", "estimated_cost", "request_approval_count", "payment_type", "advance_payment_id")
    def _compute_hide_create_approval_button(self):
        super()._compute_hide_create_approval_button()
        for rec in self:
            if rec.payment_type == "advance" and not rec.advance_payment_id:
                rec.hide_create_approval_button = True
