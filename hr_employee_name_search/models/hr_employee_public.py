from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"
    _rec_names_search = ["name", "academic_standing_name_search"]

    academic_standing_name_search = fields.Char(
        related="employee_id.academic_standing_name_search",
        readonly=True,
    )
