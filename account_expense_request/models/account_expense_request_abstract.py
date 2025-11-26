from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountExpenseRequestAbstract(models.AbstractModel):
    _name = "account.expense.request"
    _description = "Account Expense Request Abstract"

    name = fields.Char(
        string="Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
    )

    requester_id = fields.Many2one(
        comodel_name="res.partner",
        string="Requester",
        required=True,
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )

    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amount_all",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("validated", "Validated"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        default="draft",
    )

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            record.state = "submitted"
        return True

    def action_validate(self):
        """Validate the request"""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be validated."))
            record.state = "validated"
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
