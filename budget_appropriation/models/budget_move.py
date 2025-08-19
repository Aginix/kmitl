from odoo import fields, models


class BudgetMove(models.Model):
    _inherit = "budget.move"

    # Link back to budget appropriation
    appropriation_id = fields.Many2one(
        comodel_name="budget.appropriation",
        string="Source Appropriation",
        help="Budget appropriation that created this move",
        index=True,
        ondelete="set null",
    )