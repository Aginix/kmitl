from odoo import fields, models


class HrApplicantEducationHistory(models.Model):
    _name = "hr.applicant.education.history"
    _description = "Applicant Education History"
    _order = "education_level_id"

    applicant_id = fields.Many2one(
        "hr.applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    education_level_id = fields.Many2one(
        "resource.education.level",
        string="Education Level",
        required=True,
    )
    program = fields.Char()
    major = fields.Char()
    institution = fields.Char()
    country_id = fields.Many2one("res.country")
    graduation_date = fields.Date()
    certificate_file = fields.Binary(string="Certificate", attachment=True)
    certificate_filename = fields.Char()
    transcript_file = fields.Binary(string="Transcript", attachment=True)
    transcript_filename = fields.Char()
