# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequestSignature(models.Model):
    """The authorization as a signature row (the audit's is
    disbursement_payment_audit's).

    The block itself lives in ``disbursement`` and loops every row, so this
    bridge only has to declare its step and stamp it — no report
    inheritance is needed. Like every row it is archived when the request is
    reset to draft, and a re-stamp supersedes the previous row of the step.
    """

    _inherit = "disbursement.request.signature"

    step = fields.Selection(
        selection_add=[("payment_authorize", "Payment Authorizer")],
        ondelete={"payment_authorize": "cascade"},
    )
