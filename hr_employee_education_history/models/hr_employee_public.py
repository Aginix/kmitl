from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    education_level_id = fields.Many2one(
        related="employee_id.education_level_id",
        readonly=True,
    )
