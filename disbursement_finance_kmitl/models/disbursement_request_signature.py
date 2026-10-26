# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequestSignature(models.Model):
    """The two post-bill payment-execution steps as signature rows.

    The block itself lives in ``disbursement`` and loops every row, so this
    bridge only has to declare its two steps and stamp them — no report
    inheritance is needed. Like every row they are archived when the request is
    reset to draft, and a re-stamp supersedes the previous row of the step.
    """

    _inherit = "disbursement.request.signature"

    step = fields.Selection(
        selection_add=[
            ("payment_audit", "Payment Auditor"),
            ("payment_authorize", "Payment Authorizer"),
        ],
        ondelete={"payment_audit": "cascade", "payment_authorize": "cascade"},
    )
