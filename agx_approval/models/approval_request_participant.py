from odoo import api, fields, models


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

    partner_id = fields.Many2one(
        "res.partner",
        string="ชื่อ",
        required=True,
    )

    partner_type_id = fields.Many2one(
        "res.partner.type",
        string="ประเภท",
        related="partner_id.partner_type_id",
        store=True,
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
