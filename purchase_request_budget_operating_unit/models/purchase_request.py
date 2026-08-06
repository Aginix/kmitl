# -*- coding: utf-8 -*-
from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _get_budget_commitment_extra_kwargs(self):
        """Stamp the PR's operating unit onto its reservation commitment so the
        commitment lands in the same OU as the PR. Without this the commitment
        defaults to the approving user's OU and becomes invisible to PR-scoped
        users via the budget.commitment OU record rule."""
        vals = super()._get_budget_commitment_extra_kwargs()
        if self.operating_unit_id:
            vals["operating_unit_id"] = self.operating_unit_id.id
        return vals
