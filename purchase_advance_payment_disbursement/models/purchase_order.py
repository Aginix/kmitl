from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _prepare_disbursement_request_vals(self):
        vals = super()._prepare_disbursement_request_vals()
        purchase_requests = self._get_related_purchase_requests()
        for pr in purchase_requests:
            if pr.advance_payment_id:
                vals["advance_payment_id"] = pr.advance_payment_id.id
                break
        return vals
