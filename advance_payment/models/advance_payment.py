from odoo import _, api, fields, models
from odoo.exceptions import UserError

READONLY_STATES = {
    "submitted": [("readonly", True)],
    "approved": [("readonly", True)],
    "partial": [("readonly", True)],
    "fully_paid": [("readonly", True)],
    "cancel": [("readonly", True)],
}


class AdvancePayment(models.Model):
    _name = "advance.payment"
    _description = "Advance Payment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"

    name = fields.Char(
        default="/",
        readonly=True,
        copy=False,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("partial", "Partially Returned"),
            ("fully_paid", "Fully Returned"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    release_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("in_payment", "In Payment"),
            ("paid", "Paid"),
        ],
        default="pending",
        tracking=True,
    )
    type_id = fields.Many2one(
        "advance.payment.type",
        string="Type",
        states=READONLY_STATES,
        tracking=True,
    )
    reason = fields.Text(
        string="Reason",
        states=READONLY_STATES,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        states=READONLY_STATES,
        tracking=True,
    )
    amount_return = fields.Monetary(
        string="Amount Returned",
        compute="_compute_amount_return",
        store=True,
        currency_field="currency_id",
    )
    amount_residual = fields.Monetary(
        string="Residual Amount",
        compute="_compute_amount_return",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    owner_id = fields.Many2one(
        "res.users",
        string="Owner",
        default=lambda self: self.env.user,
        required=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        default=lambda self: self.env.user.employee_id,
        states=READONLY_STATES,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
        states=READONLY_STATES,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
    )
    partner_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Bank Account",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
        states=READONLY_STATES,
    )
    return_ids = fields.One2many(
        "advance.payment.return",
        "advance_payment_id",
        string="Returns",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Attachments",
    )
    loan_term = fields.Text(
        string="Loan Terms",
        default=lambda self: self.env["ir.config_parameter"]
        .sudo()
        .get_param("advance_payment.loan_term", ""),
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Payment",
        copy=False,
    )
    return_day = fields.Integer(
        string="Return Days",
        default=lambda self: int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment.default_return_days", 30)
        ),
        states=READONLY_STATES,
    )
    end_day = fields.Integer(
        string="Days Used",
        compute="_compute_end_day",
    )
    has_outstanding = fields.Boolean(
        string="Has Outstanding",
        compute="_compute_has_outstanding",
    )
    date_submitted = fields.Date(string="Submitted Date", readonly=True, copy=False)
    date_approved = fields.Date(string="Approved Date", readonly=True, copy=False)
    date_start = fields.Date(string="Payment Date", readonly=True, copy=False)
    date_due = fields.Date(
        string="Due Date",
        compute="_compute_date_due",
        store=True,
    )
    date_end = fields.Date(string="Return Date", readonly=True, copy=False)
    date_accepted = fields.Date(string="Accepted Date", readonly=True, copy=False)

    # Button visibility fields
    show_submit_button = fields.Boolean(compute="_compute_show_buttons")
    show_approve_button = fields.Boolean(compute="_compute_show_buttons")
    show_create_payment_button = fields.Boolean(compute="_compute_show_buttons")
    show_mark_paid_button = fields.Boolean(compute="_compute_show_buttons")
    show_accept_button = fields.Boolean(compute="_compute_show_buttons")
    show_cancel_button = fields.Boolean(compute="_compute_show_buttons")

    @api.depends("return_ids.amount", "return_ids.state")
    def _compute_amount_return(self):
        for rec in self:
            returned = sum(
                r.amount
                for r in rec.return_ids
                if r.state in ("validated", "done")
            )
            rec.amount_return = returned
            rec.amount_residual = rec.amount - returned

    @api.depends("employee_id")
    def _compute_from_employee(self):
        for rec in self:
            emp = rec.employee_id
            rec.department_id = emp.department_id if emp else False
            rec.partner_id = emp.address_home_id if emp else False
            rec.partner_bank_id = (
                emp.bank_account_id if emp and emp.bank_account_id else False
            )

    @api.depends("date_start", "date_end")
    def _compute_end_day(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.end_day = (rec.date_end - rec.date_start).days
            else:
                rec.end_day = 0

    @api.depends("date_start", "return_day")
    def _compute_date_due(self):
        for rec in self:
            if rec.date_start and rec.return_day:
                from datetime import timedelta

                rec.date_due = rec.date_start + timedelta(days=rec.return_day)
            else:
                rec.date_due = False

    @api.depends("employee_id", "state")
    def _compute_has_outstanding(self):
        for rec in self:
            if not rec.employee_id:
                rec.has_outstanding = False
                continue
            outstanding = self.search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("state", "in", ("approved", "partial")),
                    ("id", "!=", rec.id if rec.id else 0),
                ]
            )
            rec.has_outstanding = bool(outstanding)

    @api.depends("state", "release_state")
    def _compute_show_buttons(self):
        is_officer = self.env.user.has_group(
            "advance_payment.group_advance_payment_officer"
        )
        for rec in self:
            rec.show_submit_button = rec.state == "draft"
            rec.show_approve_button = rec.state == "submitted" and is_officer
            rec.show_create_payment_button = (
                rec.state == "approved" and rec.release_state == "pending" and is_officer
            )
            rec.show_mark_paid_button = (
                rec.state == "approved"
                and rec.release_state == "in_payment"
                and is_officer
            )
            rec.show_accept_button = (
                rec.state == "approved"
                and rec.release_state == "paid"
                and not rec.date_accepted
            )
            rec.show_cancel_button = rec.state in ("draft", "submitted") and is_officer

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("advance.payment")
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.amount or rec.amount <= 0:
                raise UserError(_("Amount must be greater than zero."))
            rec.write({"state": "submitted", "date_submitted": fields.Date.today()})

    def action_approve(self):
        self._check_officer()
        for rec in self:
            rec.write({"state": "approved", "date_approved": fields.Date.today()})

    def action_create_payment(self):
        self._check_officer()
        for rec in self:
            if not rec.partner_id:
                raise UserError(
                    _("Employee %s has no home address set.") % rec.employee_id.name
                )
            journal = self.env["account.journal"].search(
                [("type", "=", "bank"), ("company_id", "=", rec.company_id.id)],
                limit=1,
            )
            if not journal:
                raise UserError(_("No bank journal found for this company."))
            payment_vals = {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": rec.partner_id.id,
                "amount": rec.amount,
                "currency_id": rec.currency_id.id,
                "journal_id": journal.id,
                "company_id": rec.company_id.id,
                "ref": rec.name,
            }
            if rec.partner_bank_id:
                payment_vals["partner_bank_id"] = rec.partner_bank_id.id
            payment = self.env["account.payment"].create(payment_vals)
            rec.write(
                {"payment_id": payment.id, "release_state": "in_payment"}
            )
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.payment",
                "res_id": payment.id,
                "view_mode": "form",
                "target": "current",
            }

    def action_mark_paid(self):
        self._check_officer()
        for rec in self:
            rec.write(
                {"release_state": "paid", "date_start": fields.Date.today()}
            )

    def action_accept(self):
        for rec in self:
            rec.write({"date_accepted": fields.Date.today()})

    def _check_fully_returned(self):
        """Called by return model after validate/done to update state."""
        for rec in self:
            if rec.amount_residual <= 0:
                rec.state = "fully_paid"
            elif rec.amount_return > 0:
                rec.state = "partial"

    def action_cancel(self):
        self._check_officer()
        for rec in self:
            rec.state = "cancel"

    def action_reset_to_draft(self):
        for rec in self:
            rec.write(
                {
                    "state": "draft",
                    "date_submitted": False,
                    "date_approved": False,
                }
            )

    def action_open_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _check_officer(self):
        if not self.env.user.has_group(
            "advance_payment.group_advance_payment_officer"
        ):
            raise UserError(_("Only officers can perform this action."))
