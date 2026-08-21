from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        states={"draft": [("readonly", False)]},
        readonly=True,
        tracking=True,
    )
