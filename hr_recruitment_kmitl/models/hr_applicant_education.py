from odoo import fields, models


class HrApplicantEducationHistory(models.Model):
    _name = "hr.applicant.education.history"
    _description = "Applicant Education History"
    _inherit = ["hr.applicant.tracked.child"]
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
        tracking=True,
    )
    program = fields.Char(tracking=True)
    major = fields.Char(tracking=True)
    institution = fields.Char(tracking=True)
    country_id = fields.Many2one(
        "res.country",
        tracking=True,
        default=lambda self: self.env.ref("base.th", raise_if_not_found=False),
    )
    start_year = fields.Integer(tracking=True)
    graduate_year = fields.Integer(tracking=True)
    certificate_file = fields.Binary(string="Certificate", attachment=True)
    certificate_filename = fields.Char(tracking=True)
    transcript_file = fields.Binary(string="Transcript", attachment=True)
    transcript_filename = fields.Char(tracking=True)

    def _tracking_label(self):
        self.ensure_one()
        level = self.education_level_id.name or ""
        institution = self.institution or ""
        parts = [p for p in [level, institution] if p]
        return " — ".join(parts) if parts else self._description
