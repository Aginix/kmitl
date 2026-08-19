from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    method = fields.Selection(
        selection_add=[
            (
                "budget_transfer_check_procurement_plan_source",
                "Budget Transfer: dimensions match procurement plan source",
            ),
        ],
    )
