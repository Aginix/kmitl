from odoo import models


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    def _prepare_disbursement_request_vals(self):
        vals = super()._prepare_disbursement_request_vals()
        if self.request_id and self.request_id.advance_payment_id:
            vals["advance_payment_id"] = self.request_id.advance_payment_id.id
        return vals
