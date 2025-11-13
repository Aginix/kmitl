from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    purchase_request_ok = fields.Boolean(
        string="Purchase Request ",
        default=False,
        help="If checked, this product can be used in purchase requests",
    )
