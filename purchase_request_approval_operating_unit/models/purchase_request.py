from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _prepare_approval_vals(self):
        # PA must follow the PR's OU, not the acting user's default (the
        # sarabun completion path runs as the last approver).
        vals = super()._prepare_approval_vals()
        vals["operating_unit_id"] = self.operating_unit_id.id
        return vals
