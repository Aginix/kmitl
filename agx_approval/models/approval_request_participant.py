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
        domain="[('partner_type_id', 'in', allowed_partner_type_ids)]"
        " if allowed_partner_type_ids else []",
    )

    allowed_partner_type_ids = fields.Many2many(
        "res.partner.type",
        string="Allowed Partner Types",
        compute="_compute_allowed_partner_type_ids",
    )

    description = fields.Text(string="รายละเอียด")

    @api.depends(
        "request_id.category_id.allow_internal_partner",
        "request_id.category_id.allow_external_partner",
        "request_id.category_id.allow_student_partner",
    )
    def _compute_allowed_partner_type_ids(self):
        for record in self:
            category = record.request_id.category_id
            types = self.env["res.partner.type"]
            if category.allow_internal_partner:
                types |= self.env.ref("partner_type_kmitl.partner_type_employee")
            if category.allow_external_partner:
                types |= self.env.ref("partner_type_kmitl.partner_type_other")
                types |= self.env.ref("partner_type_kmitl.partner_type_company")
            if category.allow_student_partner:
                types |= self.env.ref("partner_type_kmitl.partner_type_student")
            record.allowed_partner_type_ids = types
