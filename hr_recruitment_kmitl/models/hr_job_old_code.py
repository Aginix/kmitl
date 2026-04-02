from odoo import fields, models


class HrJobOldCode(models.Model):
    _name = "hr.job.old.code"
    _description = "Job Old Code"

    name = fields.Char(string="Code", required=True)
    job_id = fields.Many2one("hr.job", ondelete="cascade", required=True)
