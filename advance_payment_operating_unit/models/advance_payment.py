from odoo import fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        states={"draft": [("readonly", False)]},
        readonly=True,
    )
