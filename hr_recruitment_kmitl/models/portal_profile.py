from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class PortalProfile(models.Model):
    _name = "portal.profile"
    _description = "Portal Profile"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # Title (related from partner)
    title = fields.Many2one(
        "res.partner.title",
        related="partner_id.title",
        readonly=False,
    )

    # Name fields (related from partner)
    first_name = fields.Char(
        string="First Name (TH)",
        related="partner_id.firstname",
        readonly=False,
    )
    middle_name = fields.Char(
        string="Middle Name (TH)",
        related="partner_id.middlename",
        readonly=False,
    )
    last_name = fields.Char(
        string="Last Name (TH)",
        related="partner_id.lastname",
        readonly=False,
    )
    first_name_en = fields.Char(string="First Name (EN)")
    middle_name_en = fields.Char(string="Middle Name (EN)")
    last_name_en = fields.Char(string="Last Name (EN)")

    # Related partner contact fields
    email = fields.Char(related="partner_id.email", readonly=False)
    phone = fields.Char(related="partner_id.phone", readonly=False)

    # Registered address (ที่อยู่ตามทะเบียนบ้าน)
    address_street = fields.Char(string="Registered Address")
    address_zip_id = fields.Many2one("res.city.zip", string="Registered ZIP Location")
    address_city = fields.Char(compute="_compute_address_fields", store=True)
    address_state_id = fields.Many2one(
        "res.country.state", compute="_compute_address_fields", store=True
    )
    address_zip = fields.Char(compute="_compute_address_fields", store=True)
    address_country_id = fields.Many2one(
        "res.country", compute="_compute_address_fields", store=True
    )
    address_address = fields.Char(
        compute="_compute_address_address", string="Registered Address (Full)"
    )

    # Current address (ที่อยู่ปัจจุบัน)
    same_as_registered_address = fields.Boolean(
        string="Same as Registered Address",
    )
    current_street = fields.Char(string="Current Address")
    current_zip_id = fields.Many2one("res.city.zip", string="Current ZIP Location")
    current_city = fields.Char(compute="_compute_current_address_fields", store=True)
    current_state_id = fields.Many2one(
        "res.country.state", compute="_compute_current_address_fields", store=True
    )
    current_zip = fields.Char(compute="_compute_current_address_fields", store=True)
    current_country_id = fields.Many2one(
        "res.country", compute="_compute_current_address_fields", store=True
    )
    current_address = fields.Char(
        compute="_compute_current_address", string="Current Address (Full)"
    )

    # Computed fields
    age = fields.Integer(compute="_compute_age")

    # Personal info
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
    spouse_prefix = fields.Many2one("res.partner.title")
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

    # Academic info
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
    ocsc_exam_filename = fields.Char(string="OCSC Exam Proof Filename")
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

    # Skills & interests
    foreign_language_skills = fields.Text()
    computer_skills = fields.Text()
    other_abilities = fields.Text()
    interests = fields.Text()

    # Education history
    highest_education = fields.Selection(
        [
            ("doctor", "ปริญญาเอก"),
            ("master", "ปริญญาโท"),
            ("bachelor", "ปริญญาตรี"),
            ("under_bachelor", "ต่ำกว่าปริญญาตรี"),
        ],
        string="Highest Education Level",
    )
    education_history_ids = fields.One2many("portal.education.history", "profile_id")

    # Work history
    work_history_ids = fields.One2many("portal.work.history", "profile_id")

    @api.depends("birthday")
    def _compute_age(self):
        today = fields.Date.today()
        for rec in self:
            if rec.birthday:
                rec.age = relativedelta(today, rec.birthday).years
            else:
                rec.age = 0

    @api.depends("address_zip_id")
    def _compute_address_fields(self):
        for rec in self:
            z = rec.address_zip_id
            rec.address_city = z.city_id.name if z else False
            rec.address_state_id = z.city_id.state_id if z else False
            rec.address_zip = z.name if z else False
            rec.address_country_id = z.city_id.country_id if z else False

    @api.depends(
        "address_street",
        "address_city",
        "address_state_id",
        "address_zip",
        "address_country_id",
    )
    def _compute_address_address(self):
        for rec in self:
            parts = [
                rec.address_street,
                rec.address_city,
                rec.address_state_id.name if rec.address_state_id else False,
                rec.address_zip,
                rec.address_country_id.name if rec.address_country_id else False,
            ]
            rec.address_address = " ".join(filter(None, parts)) or False

    @api.depends("current_zip_id")
    def _compute_current_address_fields(self):
        for rec in self:
            z = rec.current_zip_id
            rec.current_city = z.city_id.name if z else False
            rec.current_state_id = z.city_id.state_id if z else False
            rec.current_zip = z.name if z else False
            rec.current_country_id = z.city_id.country_id if z else False

    @api.depends(
        "current_street",
        "current_city",
        "current_state_id",
        "current_zip",
        "current_country_id",
    )
    def _compute_current_address(self):
        for rec in self:
            parts = [
                rec.current_street,
                rec.current_city,
                rec.current_state_id.name if rec.current_state_id else False,
                rec.current_zip,
                rec.current_country_id.name if rec.current_country_id else False,
            ]
            rec.current_address = " ".join(filter(None, parts)) or False

    @api.onchange("same_as_registered_address", "address_street", "address_zip_id")
    def _onchange_same_as_registered_address(self):
        if self.same_as_registered_address:
            self.current_street = self.address_street
            self.current_zip_id = self.address_zip_id

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.same_as_registered_address:
                current_vals = {}
                if rec.current_street != rec.address_street:
                    current_vals["current_street"] = rec.address_street
                if rec.current_zip_id != rec.address_zip_id:
                    current_vals["current_zip_id"] = rec.address_zip_id.id
                if current_vals:
                    super(PortalProfile, rec).write(current_vals)
        return res

    _sql_constraints = [
        (
            "partner_id_unique",
            "unique(partner_id)",
            "A profile already exists for this partner.",
        ),
    ]
