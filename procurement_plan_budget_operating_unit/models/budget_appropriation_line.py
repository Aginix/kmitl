# -*- coding: utf-8 -*-
from odoo import models


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    def _prepare_procurement_plan_vals(self):
        vals = super()._prepare_procurement_plan_vals()
        vals["operating_unit_id"] = self.appropriation_id.operating_unit_id.id
        return vals
