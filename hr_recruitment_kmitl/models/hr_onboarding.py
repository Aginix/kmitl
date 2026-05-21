from odoo import api, fields, models


class HrOnboarding(models.Model):
    _name = "hr.onboarding"
    _description = "HR Onboarding"
    _inherit = ["hr.applicant.tracked.child"]

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
        tracking=True,
    )
    submitted_date = fields.Datetime(readonly=True, tracking=True)

    # Blood type
    blood_type = fields.Selection(
        [("a", "A"), ("b", "B"), ("ab", "AB"), ("o", "O")], tracking=True
    )

    # Tab 3 - Family
    family_member_ids = fields.One2many(
        "hr.onboarding.family", "onboarding_id", tracking=True
    )

    # Tab 4 - Royal Decoration
    royal_decoration_id = fields.Many2one(
        "hr.employee.decoration.relation", tracking=True
    )
    royal_decoration_level = fields.Char(tracking=True)
    royal_decoration_year = fields.Integer(
        string="Royal Decoration Year (B.E.)", tracking=True
    )
    royal_decoration_agency = fields.Char(tracking=True)
    royal_decoration_proof_file = fields.Binary(attachment=True)
    royal_decoration_proof_filename = fields.Char(tracking=True)

    # Tab 5 - Work
    can_start_on_time = fields.Selection([("yes", "Yes"), ("no", "No")], tracking=True)
    starting_date = fields.Date(tracking=True)
    starting_date_note = fields.Text(tracking=True)
    starting_date_attachment_file = fields.Binary(attachment=True)
    starting_date_attachment_filename = fields.Char(tracking=True)

    # Tab 6 - Benefits
    health_employee_file = fields.Binary(attachment=True)
    health_employee_filename = fields.Char(tracking=True)
    health_family_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_onboarding_health_family_attachment_rel",
        "onboarding_id",
        "attachment_id",
        string="Health Insurance (Family) Attachments",
        tracking=True,
    )
    accident_employee_file = fields.Binary(attachment=True)
    accident_employee_filename = fields.Char(tracking=True)
    accident_family_attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_onboarding_accident_family_attachment_rel",
        "onboarding_id",
        "attachment_id",
        string="Accident Insurance (Family) Attachments",
        tracking=True,
    )
    provident_fund_file = fields.Binary(attachment=True)
    provident_fund_filename = fields.Char(tracking=True)
    beneficiary_declaration_file = fields.Binary(attachment=True)
    beneficiary_declaration_filename = fields.Char(tracking=True)
    letter_of_consent_file = fields.Binary(attachment=True)
    letter_of_consent_filename = fields.Char(tracking=True)

    # Tab 7 - Confirmation
    background_check_location_type = fields.Selection(
        [("police_hq", "Police Headquarters"), ("local_police", "Local Police")],
        tracking=True,
    )
    krungthai_bank_account = fields.Char(tracking=True)
    salary_book_file = fields.Binary(attachment=True)
    salary_book_filename = fields.Char(tracking=True)
    medical_certificate_file = fields.Binary(attachment=True)
    medical_certificate_filename = fields.Char(tracking=True)
    pdpa_consent = fields.Selection([("yes", "Yes"), ("no", "No")], tracking=True)
    final_confirm = fields.Boolean(tracking=True)

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
