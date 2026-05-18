from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrApplicantWorkHistory(models.Model):
    _name = "hr.applicant.work.history"
    _description = "Applicant Work History"
    _inherit = ["hr.applicant.tracked.child"]
    _order = "date_end desc, date_start desc"

    applicant_id = fields.Many2one(
        "hr.applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_name = fields.Char(string="Company", tracking=True)
    job_title = fields.Char(string="Job Title / Description", tracking=True)
    salary = fields.Float(tracking=True)
    date_start = fields.Date(string="Start Date", tracking=True)
    date_end = fields.Date(string="End Date", tracking=True)
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

    def _tracking_label(self):
        self.ensure_one()
        parts = [p for p in [self.company_name or "", self.job_title or ""] if p]
        return " — ".join(parts) if parts else self._description
