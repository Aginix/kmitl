from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    method = fields.Selection(
        selection_add=[
            (
                "budget_commitment_check_procurement_plan_tag",
                "Budget Commitment: procurement-plan code names its plan",
            ),
        ],
    )
