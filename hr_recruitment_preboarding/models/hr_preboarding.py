# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models


class HrPreboarding(models.Model):
    _name = "hr.preboarding"
    _description = "HR Pre-boarding"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "applicant_id"

    applicant_id = fields.Many2one(
        "hr.applicant", string="Applicant", required=True, ondelete="cascade"
    )
    token = fields.Char(
        default=lambda self: str(uuid.uuid4()), copy=False, readonly=True
    )
    portal_url = fields.Char(compute="_compute_portal_url")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    start_date = fields.Date(string="Expected Start Date")

    # Personal information
    title = fields.Selection(
        [("mr", "Mr."), ("mrs", "Mrs."), ("miss", "Miss"), ("dr", "Dr.")],
        string="Title",
    )
    first_name = fields.Char("First Name")
    last_name = fields.Char("Last Name")
    nickname = fields.Char("Nickname")
    id_card = fields.Char("ID Card Number")
    birthdate = fields.Date("Date of Birth")
    nationality = fields.Char("Nationality")
    religion = fields.Char("Religion")
    marital_status = fields.Selection(
        [
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
        ],
        string="Marital Status",
    )
    ethnicity = fields.Char("Ethnicity")

    # Address & contact
    phone = fields.Char("Phone")
    mobile = fields.Char("Mobile")
    email = fields.Char("Email")
    address = fields.Char("Address")
    city = fields.Char("City")
    zip = fields.Char("ZIP")
    country_id = fields.Many2one("res.country", "Country")

    # Bank information
    bank_name = fields.Char("Bank Name")
    bank_account_number = fields.Char("Bank Account Number")

    # Relations
    education_ids = fields.One2many(
        "hr.preboarding.education", "preboarding_id", "Education History"
    )
    document_ids = fields.One2many(
        "hr.preboarding.document", "preboarding_id", "Documents"
    )

    # HR notes and result
    hr_notes = fields.Html("HR Notes")
    employee_id = fields.Many2one(
        "hr.employee", "Created Employee", readonly=True, copy=False
    )

    @api.depends("token")
    def _compute_portal_url(self):
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        )
        for rec in self:
            rec.portal_url = f"{base_url}/preboarding/{rec.token}"

    def _create_default_documents(self):
        """Create the standard document checklist for a new preboarding record."""
        doc_names = [
            "สำเนาบัตรประจำตัวประชาชน",
            "สำเนาทะเบียนบ้าน",
            "รูปถ่าย 1 นิ้ว จำนวน 1 รูป",
            "วุฒิการศึกษา",
            "ทรานสคริปต์",
            "ใบผ่านการเกณฑ์ทหาร / ใบแสดงการยกเว้น (สำหรับผู้ชาย)",
            "สำเนาหน้าบัญชีธนาคาร",
        ]
        for name in doc_names:
            self.env["hr.preboarding.document"].create(
                {"preboarding_id": self.id, "name": name, "required": True}
            )

    def action_send_link(self):
        self.ensure_one()
        template = self.env.ref(
            "hr_recruitment_preboarding.mail_template_preboarding_link"
        )
        template.send_mail(self.id, force_send=True)

    def action_approve(self):
        self.write({"state": "approved"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_create_employee(self):
        self.ensure_one()
        applicant = self.applicant_id
        name = (
            " ".join(filter(None, [self.first_name, self.last_name]))
            or applicant.partner_name
            or applicant.name
        )
        employee = self.env["hr.employee"].create(
            {
                "name": name,
                "job_id": applicant.job_id.id,
                "department_id": applicant.department_id.id,
                "work_email": self.email or applicant.email_from,
                "mobile_phone": self.mobile,
                "private_phone": self.phone,
            }
        )
        self.write({"employee_id": employee.id})
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.employee",
            "res_id": employee.id,
            "view_mode": "form",
        }
