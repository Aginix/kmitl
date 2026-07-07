# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CashDeposit(models.Model):
    _name = "kmitl.cash.deposit"
    _description = "Cash Deposit Slip"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Deposit Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    department_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        required=True,
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    receipt_ids = fields.One2many(
        "kmitl.receipt",
        "deposit_id",
        string="Receipts",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    note = fields.Text()
    submitted_by = fields.Many2one("res.users", readonly=True, copy=False)
    submitted_date = fields.Datetime(readonly=True, copy=False)
    posted_by = fields.Many2one("res.users", readonly=True, copy=False)
    posted_date = fields.Datetime(readonly=True, copy=False)

    @api.depends("receipt_ids.amount_total")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.receipt_ids.mapped("amount_total"))

    def _get_sequence(self):
        self.ensure_one()
        return self.env["kmitl.receipt"]._get_or_create_dept_fy_sequence(
            self.department_id, self.date, "kmitl.cash.deposit", "Cash Deposit", "CD"
        )

    def action_pull_pending_receipts(self):
        """Bundle the department's confirmed receipts not yet in any deposit."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Can only pull receipts on draft deposits."))
            receipts = self.env["kmitl.receipt"].search(
                [
                    ("company_id", "=", rec.company_id.id),
                    ("department_id", "=", rec.department_id.id),
                    ("state", "=", "confirmed"),
                    ("deposit_id", "=", False),
                    ("date", "<=", rec.date),
                ]
            )
            if not receipts:
                raise UserError(
                    _("No pending confirmed receipts found for this department.")
                )
            rec.write({"receipt_ids": [(6, 0, receipts.ids)]})

    def action_submit(self):
        """Department submits the deposit slip to central finance."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft deposits can be submitted."))
            if not rec.receipt_ids:
                raise ValidationError(_("Add at least one receipt before submitting."))
            for receipt in rec.receipt_ids:
                if receipt.state != "confirmed":
                    raise ValidationError(
                        _("Receipt %s must be confirmed.") % receipt.name
                    )
                if receipt.department_id != rec.department_id:
                    raise ValidationError(
                        _("Receipt %s belongs to a different department.")
                        % receipt.name
                    )
                if receipt.company_id != rec.company_id:
                    raise ValidationError(
                        _("Receipt %s belongs to a different company.")
                        % receipt.name
                    )
                if receipt.currency_id != rec.currency_id:
                    raise ValidationError(
                        _("Receipt %s uses a different currency than the deposit.")
                        % receipt.name
                    )
            if rec.name == "/" or not rec.name:
                rec.name = rec._get_sequence().next_by_id()
            rec.write(
                {
                    "state": "submitted",
                    "submitted_by": self.env.user.id,
                    "submitted_date": fields.Datetime.now(),
                }
            )

    def action_post(self):
        """Central finance reviews and posts: every receipt in the batch gets
        its own journal entry (Dr payment-method account / Cr income)."""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted deposits can be posted."))
            for receipt in rec.receipt_ids:
                if receipt.state != "confirmed":
                    raise ValidationError(
                        _("Receipt %s is not in confirmed state.") % receipt.name
                    )
            rec.receipt_ids.action_post()
            rec.write(
                {
                    "state": "posted",
                    "posted_by": self.env.user.id,
                    "posted_date": fields.Datetime.now(),
                }
            )

    def action_cancel(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Posted deposits cannot be cancelled."))
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            if rec.state not in ("submitted", "cancelled"):
                raise UserError(_("Only submitted or cancelled deposits can reset."))
            rec.write(
                {
                    "state": "draft",
                    "submitted_by": False,
                    "submitted_date": False,
                }
            )

    def unlink(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Posted deposits cannot be deleted."))
        return super().unlink()
