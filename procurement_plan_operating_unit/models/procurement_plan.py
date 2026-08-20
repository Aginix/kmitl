# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
    )

    @api.model
    def _create_analytic_account_from_values(self, values):
        """Scope the plan's minted analytic dimension to the plan's operating unit
        so it stays visible only to the owning unit (analytic OU access rule)."""
        analytic_account = super()._create_analytic_account_from_values(values)
        if self.operating_unit_id:
            analytic_account.operating_unit_ids = [(6, 0, self.operating_unit_id.ids)]
        return analytic_account
