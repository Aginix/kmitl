from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    kid = fields.Char(
        related="employee_id.kid",
        readonly=True,
    )
