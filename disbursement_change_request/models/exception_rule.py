# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    method = fields.Selection(
        selection_add=[
            (
                "disbursement_request_check_outstanding_change_requests",
                "Disbursement Request: no outstanding change request on validation",
            ),
        ],
    )
