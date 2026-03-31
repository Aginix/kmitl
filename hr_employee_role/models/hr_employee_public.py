from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    role = fields.Selection(
        related="employee_id.role",
        readonly=True,
    )
