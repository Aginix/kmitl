# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import ValidationError

# Readonly from submission onwards, mirroring the base model's states.
READONLY_STATES = {
    "submitted": [("readonly", True)],
    "accepted": [("readonly", True)],
    "done": [("readonly", True)],
    "cancelled": [("readonly", True)],
}


class InvoiceSubmission(models.Model):
    _inherit = "kmitl.invoice.submission"

    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        required=True,
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        states=READONLY_STATES,
    )

    def _get_pending_invoice_domain(self):
        domain = super()._get_pending_invoice_domain()
        domain.append(("operating_unit_id", "=", self.operating_unit_id.id))
        return domain

    def _check_invoice_consistency(self, invoices):
        super()._check_invoice_consistency(invoices)
        for invoice in invoices:
            if invoice.operating_unit_id != self.operating_unit_id:
                raise ValidationError(
                    _("Invoice %s belongs to a different operating unit.")
                    % invoice.name
                )
