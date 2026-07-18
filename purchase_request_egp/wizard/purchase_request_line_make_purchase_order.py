from odoo import models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def make_purchase_order(self):
        res = super().make_purchase_order()
        requests = self.item_ids.mapped("line_id.request_id")
        egp_requests = requests.filtered(
            lambda r: r.is_egp and r.state == "in_progress"
        )
        if egp_requests:
            egp_requests.write({"state": "done"})
        return res
