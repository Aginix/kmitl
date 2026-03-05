from odoo import fields, models


class ProcurementType(models.Model):
    _inherit = "procurement.type"

    is_construction = fields.Boolean(
        string="Is Construction",
        default=False,
    )
