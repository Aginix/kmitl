# -*- coding: utf-8 -*-
from odoo import fields, models


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="appropriation_id.operating_unit_id",
        string="Operating Unit",
    )
