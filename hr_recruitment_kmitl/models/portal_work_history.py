from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class PortalWorkHistory(models.Model):
    _name = "portal.work.history"
    _description = "Work History"
    _order = "date_end desc, date_start desc"

    profile_id = fields.Many2one(
        "portal.profile",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_name = fields.Char(string="Company")
    job_title = fields.Char(string="Job Title / Description")
    salary = fields.Float(required=True)
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
    duration = fields.Char(compute="_compute_duration")

    @api.depends("date_start", "date_end")
    def _compute_duration(self):
        for record in self:
            if not record.date_start:
                record.duration = ""
                continue
            end = record.date_end or fields.Date.today()
            delta = relativedelta(end, record.date_start)
            parts = []
            if delta.years:
                parts.append(f"{delta.years} ปี")
            if delta.months:
                parts.append(f"{delta.months} เดือน")
            if not parts:
                parts.append("น้อยกว่า 1 เดือน")
            record.duration = " ".join(parts)

    _sql_constraints = [
        (
            "date_check",
            "CHECK(date_end IS NULL OR date_end >= date_start)",
            "End date must be after start date.",
        ),
    ]
