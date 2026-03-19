from odoo import fields, models


class BudgetAppropriationCompilationImpact(models.Model):
    _inherit = "budget.appropriation.compilation.impact"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="compilation_id.operating_unit_id",
        string="Operating Unit",
    )
