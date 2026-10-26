from odoo import api, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    @api.depends("operating_unit_id")
    def _compute_budget_verifier_candidate_ids(self):
        return super()._compute_budget_verifier_candidate_ids()

    def _get_budget_verifier_candidates(self):
        """Only confirmers of the request's own OU may be named
        ผู้ยืนยันงบประมาณที่ระบุ."""
        # sudo: regular users cannot read other users' OUs
        return (
            super()._get_budget_verifier_candidates()
            & self.operating_unit_id.sudo().user_ids
        )

    @api.constrains("operating_unit_id")
    def _check_budget_verifier_operating_unit(self):
        self._check_budget_verifier()

    @api.onchange("operating_unit_id")
    def _onchange_budget_verifier_candidates(self):
        candidates = self._get_budget_verifier_candidates()
        if self.budget_verifier_id and self.budget_verifier_id not in candidates:
            self.budget_verifier_id = False
        if not self.budget_verifier_id and len(candidates) == 1:
            self.budget_verifier_id = candidates
