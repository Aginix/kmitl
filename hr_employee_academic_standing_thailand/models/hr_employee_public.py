from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    academic_standing_id = fields.Many2one(
        related="employee_id.academic_standing_id",
        readonly=True,
    )
