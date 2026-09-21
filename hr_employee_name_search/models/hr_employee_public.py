from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    academic_standing_name_search = fields.Char(
        related="employee_id.academic_standing_name_search",
        readonly=True,
    )
