from odoo import fields, models


class AdvancePaymentMethod(models.Model):
    """Payment method for advance payment (วิธีการจ่ายเงินยืม)."""

    _name = "advance.payment.method"
    _description = "Advance Payment Method"
    _order = "name"

    name = fields.Char(string="Method Name", required=True)

    default_for_model = fields.Selection(
        selection=[("purchase.request", "Purchase Request")],
        string="Default method for",
        help="When an advance payment is created from this document type, "
        "this method will be auto-selected.",
    )

    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        ondelete="restrict",
    )

    active = fields.Boolean(default=True)
