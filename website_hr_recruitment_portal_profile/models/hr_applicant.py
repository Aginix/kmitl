import logging

from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

# Fields to copy from portal.profile to hr.applicant
PROFILE_CHAR_FIELDS = [
    "first_name_en",
    "middle_name_en",
    "last_name_en",
    "spouse_prefix",
    "spouse_first_name",
    "spouse_middle_name",
    "spouse_last_name",
    "emergency_contact_name",
    "emergency_contact_relation",
    "emergency_contact_phone",
    "emergency_contact_email",
    "ocsc_exam_number",
    "academic_position_institution",
    "street",
    "street2",
    "city",
    "zip",
]
PROFILE_TEXT_FIELDS = [
    "chronic_disease",
    "foreign_language_skills",
    "computer_skills",
    "other_abilities",
    "interests",
]
PROFILE_DATE_FIELDS = [
    "birthday",
    "academic_position_date",
    "ocsc_exam_date",
]
PROFILE_M2O_FIELDS = [
    "applicant_title",
    "nationality_id",
    "state_id",
    "country_id",
    "zip_id",
]
PROFILE_SELECTION_FIELDS = [
    "marital",
    "academic_position",
    "ocsc_exam_level",
]


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    # Name fields
    applicant_title = fields.Many2one("res.partner.title")
    first_name = fields.Char(string="First Name (TH)")
    middle_name = fields.Char(string="Middle Name (TH)")
    last_name = fields.Char(string="Last Name (TH)")
    first_name_en = fields.Char(string="First Name (EN)")
    middle_name_en = fields.Char(string="Middle Name (EN)")
    last_name_en = fields.Char(string="Last Name (EN)")

    # Address
    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one("res.country.state")
    zip = fields.Char()
    country_id = fields.Many2one("res.country")
    zip_id = fields.Many2one("res.city.zip", string="ZIP Location")

    # Personal
    birthday = fields.Date()
    nationality_id = fields.Many2one("res.country")
    marital = fields.Selection(
        [
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
        ],
        string="Marital Status",
    )
    spouse_prefix = fields.Char()
    spouse_first_name = fields.Char()
    spouse_middle_name = fields.Char()
    spouse_last_name = fields.Char()

    # Emergency contact
    emergency_contact_name = fields.Char()
    emergency_contact_relation = fields.Char()
    emergency_contact_phone = fields.Char()
    emergency_contact_email = fields.Char()

    # Health
    chronic_disease = fields.Text()

    # Academic
    academic_position = fields.Selection(
        [
            ("professor", "Professor"),
            ("associate_professor", "Associate Professor"),
            ("assistant_professor", "Assistant Professor"),
            ("lecturer", "Lecturer"),
        ],
    )
    academic_position_date = fields.Date()
    academic_position_institution = fields.Char()

    # OCSC exam
    has_ocsc_exam = fields.Boolean(string="Has OCSC Exam")
    ocsc_exam_level = fields.Selection(
        [
            ("bachelor", "Bachelor"),
            ("master", "Master"),
        ],
        string="OCSC Exam Level",
    )
    ocsc_exam_date = fields.Date(string="OCSC Exam Date")
    ocsc_exam_number = fields.Char(string="OCSC Exam Number")

    # Skills
    foreign_language_skills = fields.Text()
    computer_skills = fields.Text()
    other_abilities = fields.Text()
    interests = fields.Text()

    # History
    education_history_ids = fields.One2many(
        "hr.applicant.education.history", "applicant_id"
    )
    work_history_ids = fields.One2many("hr.applicant.work.history", "applicant_id")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._prefill_from_profile()
        return records

    def _prefill_from_profile(self):
        """Copy portal profile data into this applicant if user has a profile."""
        # Use request to get actual logged-in user, since website form
        # creates records via sudo() which changes self.env.user to superuser
        if not request:
            return
        user = request.env.user
        if not user or user._is_public():
            return
        partner = user.partner_id
        profile = (
            self.env["portal.profile"]
            .sudo()
            .search([("partner_id", "=", partner.id)], limit=1)
        )
        if not profile:
            return

        vals = {}

        # Char fields
        for field_name in PROFILE_CHAR_FIELDS:
            val = getattr(profile, field_name, False)
            if val:
                vals[field_name] = val

        # Name fields from partner
        if profile.first_name:
            vals["first_name"] = profile.first_name
        if profile.middle_name:
            vals["middle_name"] = profile.middle_name
        if profile.last_name:
            vals["last_name"] = profile.last_name

        # Text fields
        for field_name in PROFILE_TEXT_FIELDS:
            val = getattr(profile, field_name, False)
            if val:
                vals[field_name] = val

        # Date fields
        for field_name in PROFILE_DATE_FIELDS:
            val = getattr(profile, field_name, False)
            if val:
                vals[field_name] = val

        # Many2one fields
        m2o_mapping = {
            "applicant_title": "title",
            "nationality_id": "nationality_id",
            "state_id": "state_id",
            "country_id": "country_id",
            "zip_id": "zip_id",
        }
        for applicant_field, profile_field in m2o_mapping.items():
            val = getattr(profile, profile_field, False)
            if val:
                vals[applicant_field] = val.id

        # Selection fields
        for field_name in PROFILE_SELECTION_FIELDS:
            val = getattr(profile, field_name, False)
            if val:
                vals[field_name] = val

        # Boolean
        vals["has_ocsc_exam"] = profile.has_ocsc_exam

        if vals:
            self.sudo().write(vals)

        # Copy education history
        for edu in profile.education_history_ids:
            self.env["hr.applicant.education.history"].sudo().create(
                {
                    "applicant_id": self.id,
                    "level": edu.level,
                    "program": edu.program,
                    "major": edu.major,
                    "institution": edu.institution,
                    "country_id": edu.country_id.id,
                    "graduation_date": edu.graduation_date,
                }
            )

        # Copy work history
        for work in profile.work_history_ids:
            self.env["hr.applicant.work.history"].sudo().create(
                {
                    "applicant_id": self.id,
                    "company_name": work.company_name,
                    "job_title": work.job_title,
                    "salary": work.salary,
                    "date_start": work.date_start,
                    "date_end": work.date_end,
                }
            )
