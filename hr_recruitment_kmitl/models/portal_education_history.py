from odoo import fields, models


class PortalEducationHistory(models.Model):
    _name = "portal.education.history"
    _description = "Education History"
    _order = "education_level_id"

    profile_id = fields.Many2one(
        "portal.profile",
        required=True,
        ondelete="cascade",
        index=True,
    )
    education_level_id = fields.Many2one(
        "resource.education.level",
        string="Education Level",
        required=True,
    )
    program = fields.Char(required=True)
    major = fields.Char(required=True)
    institution = fields.Char(required=True)
    country_id = fields.Many2one("res.country", required=True)
    graduation_date = fields.Date(required=True)
    certificate_file = fields.Binary(string="Certificate", attachment=True)
    certificate_filename = fields.Char()
    transcript_file = fields.Binary(string="Transcript", attachment=True)
    transcript_filename = fields.Char()

    _sql_constraints = [
        (
            "profile_education_level_unique",
            "unique(profile_id, education_level_id)",
            "Only one record per education level is allowed.",
        ),
    ]
