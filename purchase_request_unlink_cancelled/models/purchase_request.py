from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _can_be_deleted(self):
        return super()._can_be_deleted() or self.state == "cancelled"
