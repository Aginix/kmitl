from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _get_budget_verifier_candidates(self):
        """Only committers of the request's own OU may be named ผู้ยืนยันงบประมาณ."""
        # sudo: regular users cannot read other users' OUs
        return (
            super()._get_budget_verifier_candidates()
            & self.operating_unit_id.sudo().user_ids
        )
