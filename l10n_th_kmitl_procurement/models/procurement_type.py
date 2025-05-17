import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProcurementType(models.Model):
    _name = "procurement.type"
    _description = "Procurement Method"
    _order = "sequence"

    name = fields.Char(
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        help="Default product for purchase request line",
    )
    active = fields.Boolean(
        default=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    description = fields.Text(
        translate=True,
    )
