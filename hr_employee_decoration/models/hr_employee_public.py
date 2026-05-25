from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    highest_decoration_id = fields.Many2one(
        related="employee_id.highest_decoration_id",
        readonly=True,
    )
