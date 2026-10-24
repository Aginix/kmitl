# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError

# Readonly from submission onwards, mirroring the base model's states.
READONLY_STATES = {
    "submitted": [("readonly", True)],
    "accepted": [("readonly", True)],
    "issued": [("readonly", True)],
    "paid": [("readonly", True)],
    "cancelled": [("readonly", True)],
}


class InvoiceKmitl(models.Model):
    _inherit = "kmitl.invoice"

    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        required=True,
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        states=READONLY_STATES,
    )

    def _prepare_move_vals(self):
        vals = super()._prepare_move_vals()
        vals["operating_unit_id"] = self.operating_unit_id.id
        return vals

    def _prepare_move_line_vals(self, line):
        vals = super()._prepare_move_line_vals(line)
        vals["operating_unit_id"] = self.operating_unit_id.id
        return vals

    def _prepare_receipt_vals(self):
        # The receipt's entry is reconciled with the invoice's: both must sit in the
        # same operating unit, not in the paying user's default one.
        vals = super()._prepare_receipt_vals()
        vals["operating_unit_id"] = self.operating_unit_id.id
        return vals

    def _get_reconcile_lines(self):
        lines = super()._get_reconcile_lines()
        # Reconciling across operating units would make account_operating_unit book
        # an inter-OU balancing entry and post it past the approval.
        if len({line.operating_unit_id for line in lines}) > 1:
            raise UserError(
                _(
                    "The entries of invoice %s belong to different operating units "
                    "and cannot be reconciled."
                )
                % self.name
            )
        return lines
