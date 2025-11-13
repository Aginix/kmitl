from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"
    bypass_warning = True

    purchase_request_ok = fields.Boolean(
        default=False,
        help="If checked, this product can be used in purchase requests",
    )
