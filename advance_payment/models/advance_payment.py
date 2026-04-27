import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

READONLY_STATES = {
    "pending": [("readonly", True)],
    "approved": [("readonly", True)],
    "done": [("readonly", True)],
    "cancel": [("readonly", True)],
}


class AdvancePayment(models.Model):
    _name = "advance.payment"
    _description = "Advance Payment (Loan Contract)"
    _inherit = [
        "analytic.distribution.mixin",
        "mail.thread",
        "mail.activity.mixin",
        "tier.validation",
    ]
    _state_from = ["draft"]
    _state_to = ["approved"]
    _tier_validation_manual_config = False
    _order = "date desc, id desc"

    name = fields.Char(
        string="Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        readonly=True,
        copy=False,
    )
    date = fields.Date(
        default=fields.Date.context_today,
        states=READONLY_STATES,
        tracking=True,
    )

    # -- Borrower Information --
    borrower_id = fields.Many2one(
        "res.users",
        string="Borrower",
        required=True,
        states=READONLY_STATES,
        tracking=True,
        default=lambda self: self.env.user,
    )
    borrower_partner_id = fields.Many2one(
        "res.partner",
        related="borrower_id.partner_id",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        states=READONLY_STATES,
        tracking=True,
    )
    partner_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Bank Account",
        states=READONLY_STATES,
        tracking=True,
        domain="[('partner_id', '=', borrower_partner_id)]",
    )
    use_attachment_bank = fields.Boolean(
        string="Use Attachment Bank Account",
    )
    bank_attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Bank Attachments",
    )

    # -- Loan Information --
    loan_type = fields.Selection(
        [
            ("procurement", "Procurement"),
            ("other", "Other"),
        ],
        string="Loan Type",
        default="other",
        states=READONLY_STATES,
        tracking=True,
    )
    loan_reason = fields.Text(
        string="Loan Reason",
        states=READONLY_STATES,
    )
    loan_amount = fields.Monetary(
        string="Loan Amount",
        currency_field="currency_id",
        states=READONLY_STATES,
        tracking=True,
    )

    # -- Standard fields --
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        readonly=True,
    )

    # -- Purchase Request Link --
    purchase_request_id = fields.Many2one(
        "purchase.request",
        string="Purchase Request",
        readonly=True,
        index=True,
    )

    # -- Disbursement link (AC4) --
    disbursement_line_ids = fields.Many2many(
        "disbursement.request.line",
        string="Expense Items",
        compute="_compute_disbursement_line_ids",
    )
    disbursement_amount_total = fields.Monetary(
        string="Total Expenses",
        currency_field="currency_id",
        compute="_compute_disbursement_line_ids",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("advance.payment") or "/"
                )
        return super().create(vals_list)

    def action_submit(self):
        self.request_validation()
        self.write({"state": "pending"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_draft(self):
        self.restart_validation()
        self.write({"state": "draft"})

    @api.depends("purchase_request_id")
    def _compute_disbursement_line_ids(self):
        DisbursementRequest = self.env["disbursement.request"]
        for rec in self:
            if rec.purchase_request_id:
                approvals = self.env["purchase.request.approval"].search(
                    [("request_id", "=", rec.purchase_request_id.id)]
                )
                disbursements = DisbursementRequest.search(
                    [("purchase_request_approval_id", "in", approvals.ids)]
                )
                rec.disbursement_line_ids = disbursements.mapped("line_ids")
                rec.disbursement_amount_total = sum(
                    disbursements.mapped("amount_total")
                )
            else:
                rec.disbursement_line_ids = False
                rec.disbursement_amount_total = 0

    def action_view_disbursement_requests(self):
        self.ensure_one()
        approvals = self.env["purchase.request.approval"].search(
            [("request_id", "=", self.purchase_request_id.id)]
        )
        disbursements = self.env["disbursement.request"].search(
            [("purchase_request_approval_id", "in", approvals.ids)]
        )
        action = {
            "type": "ir.actions.act_window",
            "name": _("Disbursement Requests"),
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": [("id", "in", disbursements.ids)],
        }
        if len(disbursements) == 1:
            action.update({"view_mode": "form", "res_id": disbursements.id})
        return action
