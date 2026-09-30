from odoo import models, fields


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    code = fields.Char("KMITL Code", copy=False, tracking=True)
