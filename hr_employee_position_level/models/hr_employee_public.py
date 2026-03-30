from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    position_level_id = fields.Many2one(
        related="employee_id.position_level_id", readonly=True
    )
    position_level_relation_id = fields.Many2one(
        related="employee_id.position_level_relation_id", readonly=True
    )
