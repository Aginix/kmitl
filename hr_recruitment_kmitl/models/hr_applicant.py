import logging

from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

# Fields to copy from portal.profile to hr.applicant
PROFILE_CHAR_FIELDS = [
    "identification_id",
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
    "address_street",
    "address_city",
    "address_zip",
    "current_street",
    "current_city",
    "current_zip",
]
PROFILE_TEXT_FIELDS = [
    "congenital_disease",
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
    "address_state_id",
    "address_country_id",
    "address_zip_id",
    "current_state_id",
    "current_country_id",
    "current_zip_id",
    "academic_standing_id",
]
PROFILE_SELECTION_FIELDS = [
    "marital",
    "ocsc_exam_level",
    "highest_education",
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

    # Registered address
    address_street = fields.Char(string="Registered Address")
    address_city = fields.Char()
    address_state_id = fields.Many2one("res.country.state")
    address_zip = fields.Char()
    address_country_id = fields.Many2one("res.country")
    address_zip_id = fields.Many2one("res.city.zip", string="Registered ZIP Location")

    # Current address
    current_street = fields.Char(string="Current Address")
    current_city = fields.Char()
    current_state_id = fields.Many2one("res.country.state")
    current_zip = fields.Char()
    current_country_id = fields.Many2one("res.country")
    current_zip_id = fields.Many2one("res.city.zip", string="Current ZIP Location")

    # Personal
    identification_id = fields.Char(string="Identification No.")
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
    congenital_disease = fields.Text()

    # Academic
    academic_standing_id = fields.Many2one(
        "hr.employee.academic.standing",
        string="Academic Position",
    )
    academic_position_date = fields.Date()
    academic_position_institution = fields.Char()
    academic_position_file = fields.Binary(
        string="Academic Position Proof", attachment=True
    )
    academic_position_filename = fields.Char(string="Academic Position Proof Filename")

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
    ocsc_exam_file = fields.Binary(string="OCSC Exam Proof", attachment=True)
    ocsc_exam_filename = fields.Char(string="OCSC Exam Filename")

    # Skills
    foreign_language_skills = fields.Text()
    computer_skills = fields.Text()
    other_abilities = fields.Text()
    interests = fields.Text()

    # History
    highest_education = fields.Selection(
        [
            ("doctor", "ปริญญาเอก"),
            ("master", "ปริญญาโท"),
            ("bachelor", "ปริญญาตรี"),
            ("under_bachelor", "ต่ำกว่าปริญญาตรี"),
        ],
        string="Highest Education Level",
    )
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
            "address_state_id": "address_state_id",
            "address_country_id": "address_country_id",
            "address_zip_id": "address_zip_id",
            "current_state_id": "current_state_id",
            "current_country_id": "current_country_id",
            "current_zip_id": "current_zip_id",
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

        # Binary fields (copy data, not link)
        if profile.ocsc_exam_file:
            vals["ocsc_exam_file"] = profile.ocsc_exam_file
            vals["ocsc_exam_filename"] = profile.ocsc_exam_filename
        if profile.academic_position_file:
            vals["academic_position_file"] = profile.academic_position_file
            vals["academic_position_filename"] = profile.academic_position_filename

        if vals:
            self.sudo().write(vals)

        # Copy education history
        for edu in profile.education_history_ids:
            self.env["hr.applicant.education.history"].sudo().create(
                {
                    "applicant_id": self.id,
                    "education_level_id": edu.education_level_id.id,
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
