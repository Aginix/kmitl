from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    relative_ids = fields.One2many(
        comodel_name="hr.employee.relative",
        inverse_name="employee_id",
    )
