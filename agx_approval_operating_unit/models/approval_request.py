from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        tracking=True,
    )

    def _get_budget_commitment_extra_kwargs(self):
        vals = super()._get_budget_commitment_extra_kwargs()
        if self.operating_unit_id:
            vals["operating_unit_id"] = self.operating_unit_id.id
        return vals
