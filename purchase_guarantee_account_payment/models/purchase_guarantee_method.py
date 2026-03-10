from odoo import fields, models


class PurchaseGuaranteeMethod(models.Model):
    _inherit = "purchase.guarantee.method"

    kmitl_payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Payment Type (KMITL)",
        help="Default KMITL payment type when creating payments from guarantees of this method",
    )
