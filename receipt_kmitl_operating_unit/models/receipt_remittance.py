# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import ValidationError

# Readonly from submission onwards, mirroring the base model's states.
READONLY_STATES = {
    "submitted": [("readonly", True)],
    "approved": [("readonly", True)],
    "posted": [("readonly", True)],
    "cancelled": [("readonly", True)],
}


class ReceiptRemittance(models.Model):
    _inherit = "kmitl.receipt.remittance"

    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        required=True,
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        states=READONLY_STATES,
    )

    def _get_pending_receipt_domain(self):
        domain = super()._get_pending_receipt_domain()
        domain.append(("operating_unit_id", "=", self.operating_unit_id.id))
        return domain

    def _check_receipt_consistency(self, receipts):
        super()._check_receipt_consistency(receipts)
        for receipt in receipts:
            if receipt.operating_unit_id != self.operating_unit_id:
                raise ValidationError(
                    _("Receipt %s belongs to a different operating unit.")
                    % receipt.name
                )
