# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        states=READONLY_STATES,
        default=lambda self: (
            self.env["res.users"].operating_unit_default_get(self.env.uid)
        ),
    )

    def budget_move_vals(self):
        vals = super().budget_move_vals()
        vals["operating_unit_id"] = self.operating_unit_id.id
        return vals
