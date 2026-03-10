from odoo import fields, models


class HrApplicantEducationHistory(models.Model):
    _name = "hr.applicant.education.history"
    _description = "Applicant Education History"
    _order = "level"

    applicant_id = fields.Many2one(
        "hr.applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    level = fields.Selection(
        [
            ("doctor", "Doctoral Degree"),
            ("master", "Master's Degree"),
            ("bachelor", "Bachelor's Degree"),
            ("under_bachelor", "Under Bachelor's Degree"),
        ],
        required=True,
    )
    program = fields.Char()
    major = fields.Char()
    institution = fields.Char()
    country_id = fields.Many2one("res.country")
    graduation_date = fields.Date()
