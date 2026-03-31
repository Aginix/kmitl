from odoo import models, fields


class OfficeOrder(models.Model):
    _inherit = "office.order"

    position_level_ids = fields.One2many(
        comodel_name="hr.employee.position.level",
        inverse_name="office_order_id",
    )
