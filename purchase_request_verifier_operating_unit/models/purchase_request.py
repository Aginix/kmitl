from odoo import api, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    @api.depends("operating_unit_id")
    def _compute_verifier_candidate_ids(self):
        """Only verifiers of the request's own OU may be named ผู้ยืนยันตรวจสอบ."""
        res = super()._compute_verifier_candidate_ids()
        for rec in self:
            # sudo: regular users cannot read other users' OUs
            rec.verifier_candidate_ids &= rec.operating_unit_id.sudo().user_ids
        return res
