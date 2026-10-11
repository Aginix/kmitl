from odoo import models


class HrEmployeeCode(models.Model):
    _inherit = "hr.employee"

    _sql_constraints = [
        (
            "code_unique",
            "unique(code)",
            "Can't be duplicate value for this field! -> 'KMITL Code'",
        )
    ]
