from odoo import fields, models


class BudgetSupportRequest(models.Model):
    _inherit = "budget.support.request"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        help="The requesting unit's Operating Unit — used for visibility/access "
        "only (decision 1, CONTEXT.md); the department dimension is what "
        "actually drives fulfilment.",
    )

    def _prepare_transfer_vals(self):
        """Transfer TO is the requester's own department — stamp the same OU
        as owner (CONTEXT.md: on Transfer the target department is the
        requester's)."""
        vals = super()._prepare_transfer_vals()
        vals["operating_unit_id"] = self.operating_unit_id.id
        return vals

    def _prepare_commitment_vals(self):
        """A Reserve keeps central's own dimension on the commitment
        (CONTEXT.md: on Reserve the commitment's own department is
        central's) — only the Beneficiary Unit is the requester's."""
        vals = super()._prepare_commitment_vals()
        vals["beneficiary_operating_unit_id"] = self.operating_unit_id.id
        return vals
