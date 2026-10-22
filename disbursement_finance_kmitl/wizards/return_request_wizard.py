# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementReturnRequestWizard(models.TransientModel):
    """The payment-execution steps' return modes, each one step back (see
    ``DisbursementRequest._return_step_handler``)."""

    _inherit = "disbursement.return.request.wizard"

    mode = fields.Selection(
        selection_add=[
            ("audit", "Audit"),
            ("authorize", "Authorize"),
            ("pay", "Pay"),
        ],
        ondelete={
            "audit": "set default",
            "authorize": "set default",
            "pay": "set default",
        },
    )
