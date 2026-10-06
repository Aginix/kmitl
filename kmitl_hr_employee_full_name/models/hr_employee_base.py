from odoo import fields, models, api


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    prefix_id = fields.Many2one("hr.employee.prefix", string="Prefix")

    firstname = fields.Char()
    lastname = fields.Char()
    middlename = fields.Char()

    firstname_secondary = fields.Char("Firstname (2nd)")
    lastname_secondary = fields.Char("Lastname (2nd)")
    middlename_secondary = fields.Char("Middlename (2nd)")

    name_secondary = fields.Char(compute="_compute_name_secondary", store=True)

    @api.depends("firstname_secondary", "middlename_secondary", "lastname_secondary")
    def _compute_name_secondary(self):
        for employee in self:
            employee.name_secondary = " ".join(
                p
                for p in (
                    employee.firstname_secondary,
                    employee.middlename_secondary,
                    employee.lastname_secondary,
                )
                if p
            )
