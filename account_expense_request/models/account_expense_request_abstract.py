from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountExpenseRequestAbstract(models.AbstractModel):
    _name = "account.expense.request"
    _inherit = ["analytic.mixin", "mail.thread", "mail.activity.mixin"]
    _description = "Account Expense Request Abstract"

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True
    )

    requester_id = fields.Many2one(
        comodel_name="res.partner",
        string="Requester",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    responsible_id = fields.Many2one(
        comodel_name="res.partner",
        string="Responsible Person",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        states=READONLY_STATES,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )

    amount_total = fields.Monetary(
        string="Amount Total",
        currency_field="currency_id",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        default="draft",
        tracking=True,
    )

    description = fields.Text(
        string="Description",
        tracking=True,
        states=READONLY_STATES,
    )

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            record.state = "submitted"
        return True

    def action_approve(self):
        """Approve the request"""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be approved."))
            record.state = "approved"
        return True

    def action_cancel(self):
        """Cancel the request"""
        for record in self:
            if record.state == "cancel":
                raise UserError(_("Request is already cancelled."))
            record.state = "cancel"
        return True

    def action_draft(self):
        """Draft the request"""
        for record in self:
            record.state = "draft"
        return True
