from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    @api.model
    def _cron_close_expired_jobs(self):
        expired = self.search(
            [
                ("date_close", "<=", fields.Datetime.now()),
                ("date_close", "!=", False),
                ("website_published", "=", True),
            ]
        )
        expired.write({"website_published": False})

    role = fields.Selection(
        [("academic", "Academic"), ("support", "Support")],
    )
    education_level_ids = fields.Many2many(
        "hr.recruitment.degree",
        string="Education Levels",
    )
    category_ids = fields.Many2many(
        "hr.job.category",
        string="Tags",
    )
    date_close = fields.Datetime(string="Closing Date")
    kmitl_employee_type = fields.Selection(
        selection=[
            ("B", "พนักงานสถาบันเงินงบประมาณ"),
            ("N", "พนักงานสถาบันเงินรายได้"),
            ("E", "พนักงานสถาบันประเภทพิเศษ"),
        ],
        string="Employee Type",
    )


class HrJobCategory(models.Model):
    _name = "hr.job.category"
    _description = "Job Category"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer()
