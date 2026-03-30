from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    master_department_id = fields.Many2one(
        related="employee_id.master_department_id", readonly=True
    )

    member_of_master_department = fields.Boolean(
        related="employee_id.member_of_master_department", readonly=True
    )
