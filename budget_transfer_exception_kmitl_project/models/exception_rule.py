from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    method = fields.Selection(
        selection_add=[
            (
                "budget_transfer_check_kmitl_project_source",
                "Budget Transfer: dimensions match KMITL project source",
            ),
        ],
    )
