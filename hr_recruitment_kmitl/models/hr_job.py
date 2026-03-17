from odoo import fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    role = fields.Selection(
        [("academic", "Academic"), ("support", "Support")],
    )
    type = fields.Selection(
        [("special", "Special"), ("academic", "Academic")], default="special"
    )
