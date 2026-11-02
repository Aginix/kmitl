# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequestSignature(models.Model):
    """The audit as a signature row, placed before the authorization's."""

    _inherit = "disbursement.request.signature"

    step = fields.Selection(
        selection_add=[("payment_audit", "Payment Auditor"), ("payment_authorize",)],
        ondelete={"payment_audit": "cascade"},
    )
