from odoo import api, fields, models


class HrOnboarding(models.Model):
    _name = "hr.onboarding"
    _description = "HR Onboarding"

    name = fields.Char(string="Onboarding Name", compute="_compute_name", store=True)
    applicant_id = fields.Many2one(
        "hr.applicant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Submitted")],
        default="draft",
    )
    submitted_date = fields.Datetime(readonly=True)

    # Blood type
    blood_type = fields.Selection([("a", "A"), ("b", "B"), ("ab", "AB"), ("o", "O")])

    # Tab 3 - Family
    family_member_ids = fields.One2many("hr.onboarding.family", "onboarding_id")

    # Tab 4 - Royal Decoration
    royal_decoration_id = fields.Many2one("hr.employee.decoration.relation")
    royal_decoration_level = fields.Integer()
    royal_decoration_year = fields.Integer(string="Royal Decoration Year (B.E.)")
    royal_decoration_agency = fields.Char()
    royal_decoration_proof_file = fields.Binary(attachment=True)
    royal_decoration_proof_filename = fields.Char()

    # Tab 5 - Work
    can_start_on_time = fields.Selection([("yes", "Yes"), ("no", "No")])
    starting_date = fields.Date()
    starting_date_note = fields.Text()
    starting_date_attachment_file = fields.Binary(attachment=True)
    starting_date_attachment_filename = fields.Char()

    # Tab 6 - Benefits
    health_employee_file = fields.Binary(attachment=True)
    health_employee_filename = fields.Char()
    health_family_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_onboarding_health_family_attachment_rel",
        "onboarding_id",
        "attachment_id",
        string="Health Insurance (Family) Attachments",
    )
    accident_employee_file = fields.Binary(attachment=True)
    accident_employee_filename = fields.Char()
    accident_family_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_onboarding_accident_family_attachment_rel",
        "onboarding_id",
        "attachment_id",
        string="Accident Insurance (Family) Attachments",
    )
    provident_fund_file = fields.Binary(attachment=True)
    provident_fund_filename = fields.Char()
    beneficiary_declaration_file = fields.Binary(attachment=True)
    beneficiary_declaration_filename = fields.Char()
    letter_of_consent_file = fields.Binary(attachment=True)
    letter_of_consent_filename = fields.Char()

    # Tab 7 - Confirmation
    background_check_location_type = fields.Selection(
        [("police_hq", "Police Headquarters"), ("local_police", "Local Police")]
    )
    krungthai_bank_account = fields.Char()
    salary_book_file = fields.Binary(attachment=True)
    salary_book_filename = fields.Char()
    medical_certificate_file = fields.Binary(attachment=True)
    medical_certificate_filename = fields.Char()
    pdpa_consent = fields.Selection([("yes", "Yes"), ("no", "No")])
    final_confirm = fields.Boolean()

    _sql_constraints = [
        (
            "applicant_id_uniq",
            "unique(applicant_id)",
            "An onboarding record already exists for this applicant.",
        )
    ]

    def action_submit(self):
        self.write({"state": "submitted", "submitted_date": fields.Datetime.now()})

    @api.depends("applicant_id")
    def _compute_name(self):
        for record in self:
            record.name = f"Onboarding - {record.applicant_id.name} ({record.applicant_id.old_code})"
