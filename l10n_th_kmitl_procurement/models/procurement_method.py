import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProcurementMethod(models.Model):
    _name = "procurement.method"
    _description = "Procurement Method"
    _order = "sequence"

    name = fields.Char(
        required=True,
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
