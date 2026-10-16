from odoo import fields, models


class PurchaseGuaranteeType(models.Model):
    _inherit = "purchase.guarantee.type"

    is_monetary = fields.Boolean(
        string="Received as Money",
        default=False,
        help="KMITL actually holds the money for this form of guarantee, so it "
        "is receipted and booked to a deposit liability. Forms that are only a "
        "promise — a bank guarantee letter — are recorded without any "
        "accounting entry.",
    )
