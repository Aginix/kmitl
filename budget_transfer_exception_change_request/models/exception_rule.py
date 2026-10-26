from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    method = fields.Selection(
        selection_add=[
            (
                "budget_transfer_check_outstanding_change_requests",
                "Budget Transfer: no outstanding change request on verification",
            ),
        ],
    )
