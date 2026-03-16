from odoo import fields, models


class PortalEducationHistory(models.Model):
    _name = "portal.education.history"
    _description = "Education History"
    _order = "level"

    profile_id = fields.Many2one(
        "portal.profile",
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
    program = fields.Char(required=True)
    major = fields.Char(required=True)
    institution = fields.Char(required=True)
    country_id = fields.Many2one("res.country", required=True)
    graduation_date = fields.Date(required=True)

    _sql_constraints = [
        (
            "profile_level_unique",
            "unique(profile_id, level)",
            "Only one record per education level is allowed.",
        ),
    ]
