from odoo import fields, models


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
    street = fields.Char(related="partner_id.street", readonly=False)
    street2 = fields.Char(related="partner_id.street2")
    city = fields.Char(related="partner_id.city")
    state_id = fields.Many2one(
        "res.country.state",
        related="partner_id.state_id",
    )
    zip = fields.Char(related="partner_id.zip")
    country_id = fields.Many2one(
        "res.country",
        related="partner_id.country_id",
        readonly=False,
    )
    zip_id = fields.Many2one(
        "res.city.zip",
        string="ZIP Location",
        related="partner_id.zip_id",
        readonly=False,
    )

    # Personal info
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

    # Academic info
    academic_position = fields.Selection(
        [
            ("professor", "Professor"),
            ("associate_professor", "Associate Professor"),
            ("assistant_professor", "Assistant Professor"),
            ("lecturer", "Lecturer"),
        ],
    )
    academic_position_date = fields.Date()

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

    # Additional personal info
    national_id = fields.Char(string="National ID")
    registered_address = fields.Text(string="Registered Address")
    current_address = fields.Text(string="Current Address")
    ethnicity = fields.Char(string="Ethnicity")
    religion = fields.Char(string="Religion")
    line_id = fields.Char(string="LINE ID")

    # Family info
    father_name = fields.Char(string="Father's Name")
    mother_name = fields.Char(string="Mother's Name")
    child_name = fields.Char(string="Child/Children's Name")

    # Skills & interests
    foreign_language_skills = fields.Text()
    computer_skills = fields.Text()
    other_abilities = fields.Text()
    interests = fields.Text()

    # Education history
    education_history_ids = fields.One2many("portal.education.history", "profile_id")

    # Work history
    work_history_ids = fields.One2many("portal.work.history", "profile_id")

    _sql_constraints = [
        (
            "partner_id_unique",
            "unique(partner_id)",
            "A profile already exists for this partner.",
        ),
    ]
