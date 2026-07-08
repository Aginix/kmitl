# -*- coding: utf-8 -*-
from odoo import models


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    def _prepare_plan_commitment_vals(self):
        """Stamp the plan's operating unit onto its reservation commitment so the
        commitment lands in the same OU as the plan (and the appropriation it was
        created from). Without this the commitment falls back to the approving
        user's default OU, which hides it — via the budget.commitment OU record
        rule — from the users scoped to the plan's own operating unit."""
        vals = super()._prepare_plan_commitment_vals()
        vals["operating_unit_id"] = self.operating_unit_id.id
        return vals
