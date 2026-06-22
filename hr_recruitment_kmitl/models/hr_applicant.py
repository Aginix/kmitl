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

    job_role = fields.Selection(related="job_id.role", string="Job Role", tracking=True)
    old_code = fields.Char(
        related="job_id.old_code", store=True, readonly=True, tracking=True
    )

    # Name fields
    applicant_title = fields.Many2one("res.partner.title", tracking=True)
    first_name = fields.Char(string="First Name (TH)", tracking=True)
    middle_name = fields.Char(string="Middle Name (TH)", tracking=True)
    last_name = fields.Char(string="Last Name (TH)", tracking=True)
    first_name_en = fields.Char(string="First Name (EN)", tracking=True)
    middle_name_en = fields.Char(string="Middle Name (EN)", tracking=True)
    last_name_en = fields.Char(string="Last Name (EN)", tracking=True)

    # Registered address
    address_street = fields.Char(string="Registered Address", tracking=True)
    address_city = fields.Char(tracking=True)
    address_state_id = fields.Many2one("res.country.state", tracking=True)
    address_zip = fields.Char(tracking=True)
    address_country_id = fields.Many2one("res.country", tracking=True)
    address_zip_id = fields.Many2one(
        "res.city.zip", string="Registered ZIP Location", tracking=True
    )

    # Current address
    current_street = fields.Char(string="Current Address", tracking=True)
    current_city = fields.Char(tracking=True)
    current_state_id = fields.Many2one("res.country.state", tracking=True)
    current_zip = fields.Char(tracking=True)
    current_country_id = fields.Many2one("res.country", tracking=True)
    current_zip_id = fields.Many2one(
        "res.city.zip", string="Current ZIP Location", tracking=True
    )

    # Personal
    identification_id = fields.Char(string="Identification No.", tracking=True)
    birthday = fields.Date(tracking=True)
    gender = fields.Selection([("male", "Male"), ("female", "Female")], tracking=True)
    nationality_id = fields.Many2one("res.country", tracking=True)
    marital = fields.Selection(
        [
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
        ],
        string="Marital Status",
        tracking=True,
    )
    spouse_prefix = fields.Char(tracking=True)
    spouse_first_name = fields.Char(tracking=True)
    spouse_middle_name = fields.Char(tracking=True)
    spouse_last_name = fields.Char(tracking=True)

    # Emergency contact
    emergency_contact_name = fields.Char(tracking=True)
    emergency_contact_relation = fields.Char(tracking=True)
    emergency_contact_phone = fields.Char(tracking=True)
    emergency_contact_email = fields.Char(tracking=True)

    # Health
    congenital_disease = fields.Text(tracking=True)

    # Academic
    academic_standing_id = fields.Many2one(
        "hr.employee.academic.standing",
        string="Academic Position",
        tracking=True,
    )
    academic_position_date = fields.Date(tracking=True)
    academic_position_institution = fields.Char(tracking=True)
    academic_position_file = fields.Binary(
        string="Academic Position Proof", attachment=True
    )
    academic_position_filename = fields.Char(
        string="Academic Position Proof Filename", tracking=True
    )

    # OCSC exam
    has_ocsc_exam = fields.Boolean(string="Has OCSC Exam", tracking=True)
    ocsc_exam_level = fields.Selection(
        [
            ("bachelor", "Bachelor"),
            ("master", "Master"),
        ],
        string="OCSC Exam Level",
        tracking=True,
    )
    ocsc_exam_date = fields.Date(string="OCSC Exam Date", tracking=True)
    ocsc_exam_number = fields.Char(string="OCSC Exam Number", tracking=True)
    ocsc_exam_file = fields.Binary(string="OCSC Exam Proof", attachment=True)
    ocsc_exam_filename = fields.Char(string="OCSC Exam Filename", tracking=True)
    resume_file = fields.Binary(string="Resume", attachment=True)
    resume_filename = fields.Char(tracking=True)
    military_certificate_file = fields.Binary(
        string="Military Certificate", attachment=True
    )
    military_certificate_filename = fields.Char(tracking=True)
    id_card_file = fields.Binary(string="ID Card", attachment=True)
    id_card_filename = fields.Char(tracking=True)
    household_registration_file = fields.Binary(
        string="Household Registration", attachment=True
    )
    household_registration_filename = fields.Char(tracking=True)
    work_certificate_file = fields.Binary(string="Work Certificate", attachment=True)
    work_certificate_filename = fields.Char(tracking=True)
    english_test_type = fields.Selection(
        [
            ("toefl_paper", "TOEFL (Paper-Based)"),
            ("toefl_computer", "TOEFL (Computer-Based)"),
            ("toefl_internet", "TOEFL (Internet-Based)"),
            ("ielts", "IELTS"),
            ("cutep", "CU-TEP"),
            ("kmitl_tep", "KMITL-TEP"),
        ],
        tracking=True,
    )
    english_test_score = fields.Char(tracking=True)
    english_test_date = fields.Date(tracking=True)
    english_test_certificate_number = fields.Char(tracking=True)
    english_score_file = fields.Binary(string="English Test Result", attachment=True)
    english_score_filename = fields.Char(tracking=True)
    other_documents_file = fields.Binary(string="Other Documents", attachment=True)
    other_documents_filename = fields.Char(tracking=True)
    photo_file = fields.Binary(string="Photo", attachment=True)
    photo_filename = fields.Char(tracking=True)

    # Confirmation documents
    exam_fee_file = fields.Binary(string="Exam Fee Receipt", attachment=True)
    exam_fee_filename = fields.Char(tracking=True)
    medical_certificate_file = fields.Binary(
        string="Medical Certificate", attachment=True
    )
    medical_certificate_filename = fields.Char(tracking=True)

    # Consent
    data_certification = fields.Boolean(tracking=True)
    pdpa_consent = fields.Boolean(string="PDPA Consent", tracking=True)

    # Skills
    foreign_language_skills = fields.Text(tracking=True)
    computer_skills = fields.Text(tracking=True)
    other_abilities = fields.Text(tracking=True)
    interests = fields.Text(tracking=True)

    # History
    highest_education = fields.Selection(
        [
            ("doctor", "ปริญญาเอก"),
            ("master", "ปริญญาโท"),
            ("bachelor", "ปริญญาตรี"),
            ("under_bachelor", "ต่ำกว่าปริญญาตรี"),
        ],
        string="Highest Education Level",
        tracking=True,
    )
    education_history_ids = fields.One2many(
        "hr.applicant.education.history", "applicant_id", tracking=True
    )
    work_history_ids = fields.One2many(
        "hr.applicant.work.history", "applicant_id", tracking=True
    )

    # Onboarding
    onboarding_ids = fields.One2many("hr.onboarding", "applicant_id", tracking=True)
    onboarding_count = fields.Integer(
        compute="_compute_onboarding_count", tracking=True
    )
    can_create_onboarding = fields.Boolean(
        compute="_compute_can_create_onboarding", tracking=True
    )

    PROFILE_REQUIRED_FIELDS = {
        "title": "คำนำหน้าชื่อ",
        "first_name": "ชื่อ (ภาษาไทย)",
        "last_name": "นามสกุล (ภาษาไทย)",
        "first_name_en": "ชื่อภาษาอังกฤษ",
        "last_name_en": "นามสกุลภาษาอังกฤษ",
        "nationality_id": "สัญชาติ",
        "identification_id": "เลขบัตรประชาชน",
        "birthday": "วัน/เดือน/ปี เกิด",
        "gender": "เพศ",
        "phone": "โทรศัพท์",
        "email": "อีเมล",
        "address_address": "ที่อยู่ตามทะเบียนบ้าน",
        "address_zip": "รหัสไปรษณีย์ที่อยู่ตามทะเบียนบ้าน",
        "current_address": "ที่อยู่ปัจจุบัน",
        "current_zip": "รหัสไปรษณีย์ที่อยู่ปัจจุบัน",
        "marital": "สถานะการสมรส",
        "emergency_contact_name": "ชื่อผู้ติดต่อฉุกเฉิน",
        "emergency_contact_relation": "ความสัมพันธ์ผู้ติดต่อฉุกเฉิน",
        "emergency_contact_phone": "เบอร์ติดต่อฉุกเฉิน",
        "emergency_contact_email": "อีเมลติดต่อฉุกเฉิน",
    }

    ROLE_REQUIRED_FIELDS = {
        "academic": {
            "academic_standing_id": "ตำแหน่งทางวิชาการ",
            "academic_position_institution": "สถาบันที่ได้รับแต่งตั้ง",
            "academic_position_date": "วันที่ได้รับแต่งตั้ง",
            "academic_position_file": "เอกสารแนบการได้รับตำแหน่งทางวิชาการ",
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
        values["partner_id"] = user.partner_id.id
        profile = (
            self.env["portal.profile"]
            .sudo()
            .search([("partner_id", "=", user.partner_id.id)], limit=1)
        )
        if not profile:
            return values
        missing = []
        # Personal info required fields
        for field_name, label in self.PROFILE_REQUIRED_FIELDS.items():
            val = getattr(profile, field_name, False)
            if not val or (isinstance(val, str) and val.strip() == "-"):
                missing.append(label)
        # Common required: education, work history, documents
        if not profile.education_history_ids:
            missing.append("ประวัติการศึกษา")
        else:
            for edu in profile.education_history_ids:
                level_name = edu.education_level_id.name or "ไม่ระบุระดับ"
                if not edu.program:
                    missing.append(
                        f"ประวัติการศึกษา ({level_name}): กรุณากรอก สาขาวิชา/โปรแกรม"
                    )
                if not edu.major:
                    missing.append(f"ประวัติการศึกษา ({level_name}): กรุณากรอก วิชาเอก/สาขา")
                if not edu.institution:
                    missing.append(
                        f"ประวัติการศึกษา ({level_name}): กรุณากรอก สถาบันการศึกษา"
                    )
                if not edu.start_year:
                    missing.append(f"ประวัติการศึกษา ({level_name}): กรุณากรอก ปีที่เริ่มศึกษา")
                if not edu.graduate_year:
                    missing.append(
                        f"ประวัติการศึกษา ({level_name}): กรุณากรอก ปีที่สำเร็จการศึกษา"
                    )
                if not edu.certificate_file:
                    missing.append(
                        f"เอกสารแนบประวัติการศึกษา ({level_name}): วุฒิบัตร/ประกาศนียบัตร"
                    )
                if not edu.transcript_file:
                    missing.append(
                        f"เอกสารแนบประวัติการศึกษา ({level_name}): ใบแสดงผลการศึกษา (Transcript)"
                    )
        if profile.work_history_ids:
            for i, work in enumerate(profile.work_history_ids, start=1):
                fields = []
                if not work.company_name:
                    fields.append("ชื่อสถานที่ทำงาน")
                if not work.job_title:
                    fields.append("ตำแหน่ง")
                if not work.salary:
                    fields.append("เงินเดือน")
                if not work.date_start:
                    fields.append("วันที่เริ่มงาน")
                if fields:
                    company = work.company_name or f"งานที่ {i}"
                    missing.append(f"{company}: กรุณากรอก {', '.join(fields)}")
        # Role-specific required fields
        if job.role:
            required = dict(self.ROLE_REQUIRED_FIELDS.get(job.role, {}))
            if job.role == "support" and profile.has_ocsc_exam:
                required.update(self.OCSC_CONDITIONAL_FIELDS)
                if not profile.ocsc_exam_file:
                    missing.append("เอกสารแนบการสอบ ก.พ.: ไฟล์ใบรับรองผลสอบ ก.พ.")
            for field_name, label in required.items():
                if not getattr(profile, field_name, False):
                    missing.append(label)
        if not profile.photo_file:
            missing.append("รูปถ่ายหน้าตรง")
        if not profile.id_card_file:
            missing.append("สำเนาบัตรประจำตัวประชาชน")
        if not profile.household_registration_file:
            missing.append("สำเนาทะเบียนบ้าน")
        if profile.gender == "male" and not profile.military_certificate_file:
            missing.append("สำเนาหนังสือรับรองผ่านการเกณฑ์ทหาร")
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
                    "start_year": edu.start_year,
                    "graduate_year": edu.graduate_year,
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
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "hr_recruitment_kmitl.action_hr_onboarding"
        )
        action["domain"] = [
            ("applicant_id", "=", self.id),
            ("applicant_id.job_id", "=", self.job_id.id),
        ]
        action["context"] = {
            "default_applicant_id": self.id,
        }
        onboardings = self.onboarding_ids
        if len(onboardings) == 1:
            action["views"] = [
                (
                    self.env.ref("hr_recruitment_kmitl.hr_onboarding_view_form").id,
                    "form",
                ),
            ]
            action["res_id"] = onboardings.id
        return action

    def create_employee_from_applicant(self):
        action = super().create_employee_from_applicant()
        self.ensure_one()
        context = dict(action.get("context") or {})
        context.update(self._employee_default_context())
        action["context"] = context
        return action

    def _employee_default_context(self):
        """Build default_* context keys to pre-fill the new employee form."""
        self.ensure_one()
        ctx = {}
        scalar_map = {
            "first_name": "default_firstname",
            "middle_name": "default_middlename",
            "last_name": "default_lastname",
            "first_name_en": "default_firstname_secondary",
            "middle_name_en": "default_middlename_secondary",
            "last_name_en": "default_lastname_secondary",
            "identification_id": "default_identification_id",
            "birthday": "default_birthday",
            "gender": "default_gender",
            "marital": "default_marital",
            "partner_mobile": "default_mobile_phone",
            "email_from": "default_private_email",
        }
        for src, dest in scalar_map.items():
            val = getattr(self, src, False)
            if val:
                ctx[dest] = val
        if self.nationality_id:
            ctx["default_country_id"] = self.nationality_id.id
        prefix = self._resolve_employee_prefix()
        if prefix:
            ctx["default_prefix_id"] = prefix.id
        if self.job_id and self.job_id.role:
            ctx["default_role"] = self.job_id.role
        return ctx

    def _resolve_employee_prefix(self):
        """Pick the hr.employee.prefix to apply on the new employee.

        Academic position (วิทยฐานะ) takes precedence over the personal
        title so the employee's name is prefixed with the academic rank
        when present; the academic_standing_id table itself is left empty.
        """
        self.ensure_one()
        Prefix = self.env["hr.employee.prefix"].sudo()
        candidate_names = []
        if self.academic_standing_id:
            candidate_names.append(self.academic_standing_id.name)
        if self.applicant_title:
            candidate_names.append(self.applicant_title.name)
        for name in candidate_names:
            if not name:
                continue
            prefix = Prefix.search([("name", "=", name)], limit=1)
            if prefix:
                return prefix
        return Prefix.browse()

    def _update_employee_from_applicant(self):
        for applicant in self:
            employee = applicant.emp_id
            if not employee:
                continue
            applicant._sync_employee_prefix(employee)
            applicant._sync_employee_education_history(employee)
            onboarding = applicant.onboarding_ids[:1]
            if onboarding:
                applicant._sync_employee_relatives(employee, onboarding)
                applicant._sync_employee_decoration(employee, onboarding)
        return super()._update_employee_from_applicant()

    def _sync_employee_prefix(self, employee):
        # Employee prefix_id is hr.employee.prefix. Prefer the academic
        # position (วิทยฐานะ) over the personal title — see
        # _resolve_employee_prefix.
        if not hasattr(employee, "prefix_id"):
            return
        prefix = self._resolve_employee_prefix()
        if prefix:
            employee.sudo().prefix_id = prefix.id

    def _sync_employee_education_history(self, employee):
        if not self.education_history_ids or not hasattr(
            employee, "education_history_ids"
        ):
            return
        Edu = self.env["hr.employee.education.history"].sudo()
        year_keys = {key for key, _label in Edu.year_selection()}
        for edu in self.education_history_ids:
            vals = {"employee_id": employee.id}
            if edu.education_level_id:
                vals["education_level_id"] = edu.education_level_id.id
            if edu.graduate_year:
                year = str(edu.graduate_year)
                if year in year_keys:
                    vals["graduation_year"] = year
            Edu.create(vals)

    def _sync_employee_relatives(self, employee, onboarding):
        if not onboarding.family_member_ids or not hasattr(employee, "relative_ids"):
            return
        Relative = self.env["hr.employee.relative"].sudo()
        for member in onboarding.family_member_ids:
            Relative.create(
                {
                    "employee_id": employee.id,
                    "relation_id": member.relation_id.id,
                    "identification_id": member.identification_id,
                    "prefix_id": member.prefix_id.id if member.prefix_id else False,
                    "firstname": member.first_name,
                    "middlename": member.middle_name,
                    "lastname": member.last_name,
                    "date_of_birth": member.date_of_birth,
                    "job": member.job,
                    "phone": member.phone,
                    "status": member.status,
                }
            )

    def _sync_employee_decoration(self, employee, onboarding):
        if not onboarding.royal_decoration_id or not hasattr(
            employee, "decoration_ids"
        ):
            return
        # Onboarding has no effective date; fall back to the applicant's
        # creation date (or today) to satisfy the required field on
        # hr.employee.decoration. HR can correct it afterwards.
        effective_date = (
            self.create_date.date() if self.create_date else fields.Date.today()
        )
        self.env["hr.employee.decoration"].sudo().create(
            {
                "employee_id": employee.id,
                "relation_id": onboarding.royal_decoration_id.id,
                "effective_date": effective_date,
            }
        )
