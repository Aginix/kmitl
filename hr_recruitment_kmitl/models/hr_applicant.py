import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
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
    "english_test_score",
    "english_test_certificate_number",
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
    "english_test_date",
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
    "gender",
    "marital",
    "ocsc_exam_level",
    "highest_education",
    "english_test_type",
]

# Role-specific fields to skip when copying from profile
ACADEMIC_ONLY_FIELDS = {
    "academic_standing_id",
    "academic_position_date",
    "academic_position_institution",
    "english_test_type",
    "english_test_score",
    "english_test_date",
    "english_test_certificate_number",
    "academic_position_file",
    "academic_position_filename",
    "english_score_file",
    "english_score_filename",
    "resume_file",
    "resume_filename",
    "work_certificate_file",
    "work_certificate_filename",
}

SUPPORT_ONLY_FIELDS = {
    "has_ocsc_exam",
    "ocsc_exam_level",
    "ocsc_exam_date",
    "ocsc_exam_number",
    "ocsc_exam_file",
    "ocsc_exam_filename",
    "foreign_language_skills",
    "computer_skills",
    "other_abilities",
    "interests",
}


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    job_role = fields.Selection(related="job_id.role", string="Job Role")
    old_code = fields.Char()

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
    gender = fields.Selection([("male", "Male"), ("female", "Female")])
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
    resume_file = fields.Binary(string="Resume", attachment=True)
    resume_filename = fields.Char()
    military_certificate_file = fields.Binary(
        string="Military Certificate", attachment=True
    )
    military_certificate_filename = fields.Char()
    id_card_file = fields.Binary(string="ID Card", attachment=True)
    id_card_filename = fields.Char()
    household_registration_file = fields.Binary(
        string="Household Registration", attachment=True
    )
    household_registration_filename = fields.Char()
    work_certificate_file = fields.Binary(string="Work Certificate", attachment=True)
    work_certificate_filename = fields.Char()
    english_test_type = fields.Selection(
        [
            ("toefl_paper", "TOEFL (Paper-Based)"),
            ("toefl_computer", "TOEFL (Computer-Based)"),
            ("toefl_internet", "TOEFL (Internet-Based)"),
            ("ielts", "IELTS"),
            ("cutep", "CU-TEP"),
            ("kmitl_tep", "KMITL-TEP"),
        ],
    )
    english_test_score = fields.Char()
    english_test_date = fields.Date()
    english_test_certificate_number = fields.Char()
    english_score_file = fields.Binary(string="English Test Result", attachment=True)
    english_score_filename = fields.Char()
    other_documents_file = fields.Binary(string="Other Documents", attachment=True)
    other_documents_filename = fields.Char()
    photo_file = fields.Binary(string="Photo", attachment=True)
    photo_filename = fields.Char()

    # Confirmation documents
    exam_fee_file = fields.Binary(string="Exam Fee Receipt", attachment=True)
    exam_fee_filename = fields.Char()
    medical_certificate_file = fields.Binary(
        string="Medical Certificate", attachment=True
    )
    medical_certificate_filename = fields.Char()

    # Consent
    data_certification = fields.Boolean()
    pdpa_consent = fields.Boolean(string="PDPA Consent")

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

    # Onboarding
    onboarding_ids = fields.One2many("hr.onboarding", "applicant_id")
    onboarding_count = fields.Integer(compute="_compute_onboarding_count")
    can_create_onboarding = fields.Boolean(compute="_compute_can_create_onboarding")

    ROLE_REQUIRED_FIELDS = {
        "academic": {
            "academic_standing_id": "ตำแหน่งทางวิชาการ",
            "academic_position_institution": "สถาบันที่ได้รับแต่งตั้ง",
            "academic_position_date": "วันที่ได้รับแต่งตั้ง",
        },
        "support": {
            "has_ocsc_exam": "สถานะการสอบ ก.พ.",
        },
    }

    OCSC_CONDITIONAL_FIELDS = {
        "ocsc_exam_level": "ระดับการสอบ ก.พ.",
        "ocsc_exam_date": "วันที่สอบผ่าน ก.พ.",
        "ocsc_exam_number": "เลขที่ใบรับรอง ก.พ.",
    }

    def website_form_input_filter(self, request, values):
        """Validate required fields and set default name."""
        # Auto-generate subject from partner_name
        if not values.get("name") and values.get("partner_name"):
            values["name"] = values["partner_name"]
        job_id = values.get("job_id")
        if not job_id:
            return values
        job = self.env["hr.job"].browse(int(job_id))
        if not job.exists():
            return values
        user = request.env.user
        if user._is_public():
            return values
        profile = (
            self.env["portal.profile"]
            .sudo()
            .search([("partner_id", "=", user.partner_id.id)], limit=1)
        )
        if not profile:
            return values
        missing = []
        # Common required: education, work history, documents
        if not profile.education_history_ids:
            missing.append("ประวัติการศึกษา")
        if not profile.id_card_file:
            missing.append("สำเนาบัตรประจำตัวประชาชน")
        if not profile.household_registration_file:
            missing.append("สำเนาทะเบียนบ้าน")
        if not profile.photo_file:
            missing.append("รูปถ่ายหน้าตรง")
        if profile.gender == "male" and not profile.military_certificate_file:
            missing.append("สำเนาหนังสือรับรองผ่านการเกณฑ์ทหาร")
        # Role-specific required fields
        if job.role:
            required = dict(self.ROLE_REQUIRED_FIELDS.get(job.role, {}))
            if job.role == "support" and profile.has_ocsc_exam:
                required.update(self.OCSC_CONDITIONAL_FIELDS)
            for field_name, label in required.items():
                if not getattr(profile, field_name, False):
                    missing.append(label)
        # Consent & file validation — check raw request data directly
        # because extract_data may not put them in values if fields
        # aren't in authorized_fields yet
        req_form = request.httprequest.form
        req_files = request.httprequest.files
        if req_form.get("data_certification") != "true":
            missing.append("การรับรองข้อมูล")
        if req_form.get("pdpa_consent") != "true":
            missing.append("ข้อตกลง PDPA")
        if not any(k.startswith("exam_fee_file") for k in req_files):
            missing.append("ค่าธรรมเนียมการสอบ")
        if not any(k.startswith("medical_certificate_file") for k in req_files):
            missing.append("ใบรับรองแพทย์")
        # extract_data only auto-fills filenames for "manual" fields,
        # so Python-defined fields need it set explicitly.
        filename_field_by_input = {
            "exam_fee_file": "exam_fee_filename",
            "medical_certificate_file": "medical_certificate_filename",
        }
        for key, fs in req_files.items():
            base = key.split("[", 1)[0]
            filename_field = filename_field_by_input.get(base)
            if filename_field and fs.filename:
                values[filename_field] = fs.filename
        if missing:
            raise UserError(_("กรุณากรอกข้อมูลให้ครบถ้วน:\n• " + "\n• ".join(missing)))
        return values

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
        if profile.resume_file:
            vals["resume_file"] = profile.resume_file
            vals["resume_filename"] = profile.resume_filename
        if profile.military_certificate_file:
            vals["military_certificate_file"] = profile.military_certificate_file
            vals["military_certificate_filename"] = (
                profile.military_certificate_filename
            )
        if profile.id_card_file:
            vals["id_card_file"] = profile.id_card_file
            vals["id_card_filename"] = profile.id_card_filename
        if profile.household_registration_file:
            vals["household_registration_file"] = profile.household_registration_file
            vals["household_registration_filename"] = (
                profile.household_registration_filename
            )
        if profile.work_certificate_file:
            vals["work_certificate_file"] = profile.work_certificate_file
            vals["work_certificate_filename"] = profile.work_certificate_filename
        if profile.english_score_file:
            vals["english_score_file"] = profile.english_score_file
            vals["english_score_filename"] = profile.english_score_filename
        if profile.other_documents_file:
            vals["other_documents_file"] = profile.other_documents_file
            vals["other_documents_filename"] = profile.other_documents_filename
        if profile.photo_file:
            vals["photo_file"] = profile.photo_file
            vals["photo_filename"] = profile.photo_filename

        # Filter out fields not relevant to the job role
        role = self.job_id.role
        if role == "academic":
            for f in SUPPORT_ONLY_FIELDS:
                vals.pop(f, None)
        elif role == "support":
            for f in ACADEMIC_ONLY_FIELDS:
                vals.pop(f, None)

        # Auto-fill old_code if the job has exactly 1 position
        if self.job_id and len(self.job_id.old_code_ids) == 1:
            vals["old_code"] = self.job_id.old_code_ids.name

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
                    "certificate_file": edu.certificate_file,
                    "certificate_filename": edu.certificate_filename,
                    "transcript_file": edu.transcript_file,
                    "transcript_filename": edu.transcript_filename,
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

    def _compute_onboarding_count(self):
        for record in self:
            record.onboarding_count = len(record.onboarding_ids)

    @api.depends("stage_id", "onboarding_ids")
    def _compute_can_create_onboarding(self):
        hired_stage = self.env.ref(
            "hr_recruitment.stage_job4", raise_if_not_found=False
        )
        for record in self:
            record.can_create_onboarding = bool(
                hired_stage
                and record.stage_id.id == hired_stage.id
                and not record.onboarding_ids
            )

    def action_view_onboarding(self):
        self.ensure_one()
        return self.env["ir.actions.act_window"]._for_xml_id(
            "hr_recruitment_kmitl.action_hr_onboarding"
        )
