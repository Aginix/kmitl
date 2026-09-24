from odoo import fields, models


class HrEmployeePublic(models.AbstractModel):
    _inherit = "hr.employee.public"

    prefix_id = fields.Many2one(related="employee_id.prefix_id", readonly=True)

    firstname = fields.Char(related="employee_id.firstname", readonly=True)
    lastname = fields.Char(related="employee_id.lastname", readonly=True)
    middlename = fields.Char(related="employee_id.middlename", readonly=True)

    firstname_secondary = fields.Char(
        related="employee_id.firstname_secondary", readonly=True
    )
    lastname_secondary = fields.Char(
        related="employee_id.lastname_secondary", readonly=True
    )
    middlename_secondary = fields.Char(
        related="employee_id.middlename_secondary", readonly=True
    )

    name_secondary = fields.Char(related="employee_id.name_secondary", readonly=True)
