from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AdvancePaymentAgreement(models.Model):
    """
    Advance Payment Agreement (สัญญายืมเงิน).

    Tracks the full lifecycle of employee advance payment loans:
    draft → in_progress → in_review → done / cancelled
    """

    _name = "advance.payment.agreement"
    _description = "Advance Payment Agreement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc, id desc"

    READONLY_STATES = {
        "in_progress": [("readonly", True)],
        "in_review": [("readonly", True)],
        "done": [("readonly", True)],
        "cancelled": [("readonly", True)],
    }

    name = fields.Char(
        string="Agreement Number",
        copy=False,
        tracking=True,
        default=lambda self: _("New"),
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("in_review", "In Review"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    confirmed = fields.Boolean(copy=False, tracking=True)

    origin_reference = fields.Char(
        string="Reference",
        placeholder="เลขที่ใบขอซื้อ/จ้าง",
        states=READONLY_STATES,
    )

    borrower_name = fields.Char(
        string="Borrower Name",
        required=True,
        states=READONLY_STATES,
    )

    academic_position = fields.Char(
        string="Academic Position",
        states=READONLY_STATES,
    )

    department = fields.Char(
        string="Department",
        states=READONLY_STATES,
    )

    sub_department = fields.Char(
        string="Sub-Department",
        states=READONLY_STATES,
    )

    loan_reason = fields.Text(
        string="Loan Reason",
        states=READONLY_STATES,
    )

    loan_type_id = fields.Many2one(
        comodel_name="advance.payment.loan.type",
        string="Loan Type",
        states=READONLY_STATES,
    )

    loan_amount = fields.Monetary(
        string="Loan Amount",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    bank_account_number = fields.Char(
        string="Bank Account Number",
        states=READONLY_STATES,
    )

    bank_id = fields.Many2one(
        comodel_name="advance.payment.bank",
        string="Bank",
        states=READONLY_STATES,
    )

    usage_line_ids = fields.One2many(
        comodel_name="advance.payment.usage.line",
        inverse_name="agreement_id",
        string="Usage Records",
        readonly=True,
    )

    amount_used = fields.Monetary(
        string="Amount Used",
        compute="_compute_amounts",
        store=True,
    )

    amount_remaining = fields.Monetary(
        string="Amount Remaining",
        compute="_compute_amounts",
        store=True,
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "advance.payment.agreement")],
    )

    @api.depends("loan_amount", "usage_line_ids.amount")
    def _compute_amounts(self):
        for rec in self:
            used = sum(rec.usage_line_ids.mapped("amount"))
            rec.amount_used = used
            rec.amount_remaining = rec.loan_amount - used

    def action_confirm(self):
        """Generate sequence and mark as confirmed (ยืนยันส่งข้อมูล)."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft agreements can be confirmed."))
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code(
                    "advance.payment.agreement"
                )
            rec.confirmed = True

    def action_approve(self):
        """Approve the agreement and move to in_progress (อนุมัติ)."""
        for rec in self:
            if rec.state != "draft" or not rec.confirmed:
                raise UserError(
                    _("Only confirmed draft agreements can be approved.")
                )
            rec.state = "in_progress"

    def action_close(self):
        """Close the agreement (ปิดสัญญา)."""
        for rec in self:
            if rec.state != "in_review":
                raise UserError(_("Only agreements in review can be closed."))
            rec.state = "done"

    def action_cancel(self):
        """Cancel the agreement (ยกเลิก)."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft agreements can be cancelled."))
            rec.state = "cancelled"

    def action_reset_to_draft(self):
        """Reset cancelled agreement back to draft."""
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(_("Only cancelled agreements can be reset to draft."))
            rec.state = "draft"
            rec.confirmed = False

    def action_open_usage_wizard(self):
        """Open wizard to record usage of advance payment."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("บันทึกการใช้เงิน"),
            "res_model": "advance.payment.usage.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_agreement_id": self.id},
        }

    def action_open_return_wizard(self):
        """Open wizard to confirm money return."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("คืนเงิน"),
            "res_model": "advance.payment.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_agreement_id": self.id},
        }
