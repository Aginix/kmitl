from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ApprovalRequestParticipant(models.Model):
    """รายชื่อ — people involved in the activity (travellers, attendees,
    related persons). A roster captured on the plan; it carries no bank and
    no amount. Recipients for the actual disbursement are later chosen from
    this roster (see approval.request.allocation)."""

    _name = "approval.request.participant"
    _description = "Approval Request Participant"
    _order = "sequence, id"

    sequence = fields.Integer(string="Sequence", default=10)

    request_id = fields.Many2one(
        "approval.request",
        string="Request",
        required=True,
        ondelete="cascade",
    )

    participant_type = fields.Selection(
        [("internal", "บุคลากรภายใน"), ("student", "นักศึกษา")],
        required=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="ชื่อ",
        required=True,
        domain="[('partner_type_id', 'in', allowed_partner_type_ids)]",
    )

    allowed_partner_type_ids = fields.Many2many(
        "res.partner.type",
        string="Allowed Partner Types",
        compute="_compute_allowed_partner_type_ids",
    )

    partner_type_id = fields.Many2one(
        "res.partner.type",
        string="ประเภท",
        related="partner_id.partner_type_id",
    )

    phone = fields.Char(string="โทรศัพท์", related="partner_id.phone")

    vat = fields.Char(
        string="เลขผู้เสียภาษี/บัตร ปชช.", related="partner_id.vat"
    )

    employee_department_name = fields.Char(
        string="หน่วยงาน", compute="_compute_employee_info"
    )

    employee_job_name = fields.Char(
        string="ตำแหน่ง", compute="_compute_employee_info"
    )

    description = fields.Text(string="รายละเอียด")

    @api.depends(
        "participant_type", "request_id.category_id.allowed_partner_type_ids"
    )
    def _compute_allowed_partner_type_ids(self):
        """The category's partner types (all if it sets none), narrowed to
        internal types for staff or to the student type for students."""
        all_types = self.env["res.partner.type"].search([])
        student = self.env.ref(
            "partner_type_kmitl.partner_type_student", raise_if_not_found=False
        )
        for participant in self:
            types = (
                participant.request_id.category_id.allowed_partner_type_ids
                or all_types
            )
            if participant.participant_type == "internal":
                types = types.filtered("is_internal")
            else:
                types = types & student if student else types.browse()
            participant.allowed_partner_type_ids = types

    @api.constrains("partner_id", "participant_type")
    def _check_partner_type_allowed(self):
        for participant in self:
            if (
                participant.partner_id.partner_type_id
                not in participant.allowed_partner_type_ids
            ):
                raise ValidationError(
                    _(
                        "%(partner)s is not an allowed contact type for this participant.",
                        partner=participant.partner_id.display_name,
                    )
                )

    @api.depends("partner_id")
    def _compute_employee_info(self):
        employees = self.env["hr.employee"].sudo().search(
            [("work_contact_id", "in", self.partner_id.ids)]
        )
        employee_by_partner = {
            employee.work_contact_id.id: employee for employee in employees
        }
        for participant in self:
            employee = employee_by_partner.get(participant.partner_id.id)
            participant.employee_department_name = (
                employee.department_id.name if employee else False
            )
            participant.employee_job_name = (
                employee.job_id.name if employee else False
            )
