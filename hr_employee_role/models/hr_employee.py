from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    role = fields.Selection(
        [
            ("academic", "Academic"),
            ("support", "Support"),
        ],
    )
