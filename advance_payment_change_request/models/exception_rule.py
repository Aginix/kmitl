from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    method = fields.Selection(
        selection_add=[
            (
                "advance_payment_check_outstanding_change_requests",
                "Advance Payment: no outstanding change request on verify",
            ),
        ],
    )
