# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ReceiptKmitl(models.Model):
    _name = "receipt.kmitl"
    _description = "KMITL Cash Receipt"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    READONLY_STATES = {
        "issued": [("readonly", True)],
        "deposited": [("readonly", True)],
        "reclassified": [("readonly", True)],
        "cancelled": [("readonly", True)],
    }

    name = fields.Char(
        string="Receipt Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("deposited", "Deposited"),
            ("reclassified", "Reclassified"),
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
        states=READONLY_STATES,
    )
    department_id = fields.Many2one(
        "account.analytic.account",
        string="Issuing Department",
        required=True,
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        states=READONLY_STATES,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain=[("is_receipt_kmitl_journal", "=", True)],
        tracking=True,
        states=READONLY_STATES,
    )
    payment_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("transfer", "Bank Transfer"),
            ("card", "Card"),
            ("cheque", "Cheque"),
        ],
        required=True,
        default="cash",
        tracking=True,
        states=READONLY_STATES,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        default=lambda self: self._default_partner_id(),
        tracking=True,
        states=READONLY_STATES,
    )
    customer_name = fields.Char(
        string="Customer Name (snapshot)",
        tracking=True,
        states=READONLY_STATES,
    )
    customer_tax_id = fields.Char(
        string="Tax ID (snapshot)",
        states=READONLY_STATES,
    )
    customer_address = fields.Text(
        string="Customer Address (snapshot)",
        states=READONLY_STATES,
    )
    customer_branch_code = fields.Char(
        string="Branch Code (snapshot)",
        states=READONLY_STATES,
    )
    note = fields.Text(states=READONLY_STATES)
    line_ids = fields.One2many(
        "receipt.kmitl.line",
        "receipt_id",
        string="Lines",
        copy=True,
        states=READONLY_STATES,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        states=READONLY_STATES,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        states=READONLY_STATES,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    cash_deposit_id = fields.Many2one(
        "receipt.kmitl.cash.deposit",
        string="Cash Deposit",
        readonly=True,
        copy=False,
    )
    cancel_reason = fields.Text(readonly=True, copy=False)
    cancelled_by = fields.Many2one("res.users", readonly=True, copy=False)
    cancelled_date = fields.Datetime(readonly=True, copy=False)
    user_id = fields.Many2one(
        "res.users",
        string="Issued By",
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True,
        copy=False,
    )

    @api.model
    def _default_partner_id(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "receipt_kmitl.walkin_partner_id"
        )
        if param:
            try:
                return int(param)
            except (TypeError, ValueError):
                return False
        return self.env.ref(
            "receipt_kmitl.partner_walkin", raise_if_not_found=False
        ).id or False

    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("amount"))

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for rec in self:
            if not rec.partner_id:
                continue
            partner = rec.partner_id
            rec.customer_name = partner.name or rec.customer_name
            rec.customer_tax_id = partner.vat or rec.customer_tax_id
            address_parts = [
                partner.street,
                partner.street2,
                partner.city,
                partner.state_id.name if partner.state_id else None,
                partner.zip,
            ]
            address = ", ".join([p for p in address_parts if p])
            if address:
                rec.customer_address = address
            # l10n_th branch code (optional, not required dependency)
            if hasattr(partner, "branch") and partner.branch:
                rec.customer_branch_code = partner.branch

    @api.constrains("line_ids", "state")
    def _check_lines_when_issued(self):
        for rec in self:
            if rec.state in ("issued", "deposited", "reclassified") and not rec.line_ids:
                raise ValidationError(_("A receipt must have at least one line."))

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    def _get_fiscal_year_suffix(self, date):
        """Thai fiscal year suffix (2 digits) from a date.

        Thai fiscal year runs Oct → Sep. Returns the Buddhist Era + 543 last 2 digits
        of the budget year. Example: 2025-10-01 → FY 2569 → '69'."""
        budget_year_ce = date.year + (1 if date.month >= 10 else 0)
        budget_year_be = budget_year_ce + 543
        return str(budget_year_be)[-2:]

    def _get_receipt_sequence(self, department, date):
        """Lazy-create per-(dept_code, fiscal_year) ir.sequence."""
        dept_code = department.code or "00"
        fy_suffix = self._get_fiscal_year_suffix(date)
        seq_code = "receipt.kmitl.%s.%s" % (dept_code, fy_suffix)
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "Receipt %s FY%s" % (dept_code, fy_suffix),
                    "code": seq_code,
                    "prefix": "RC/%s/%s/" % (dept_code, fy_suffix),
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_issue(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft receipts can be issued."))
            if not rec.line_ids:
                raise ValidationError(_("Add at least one line before issuing."))
            for line in rec.line_ids:
                if not line.suspense_account_id:
                    raise ValidationError(
                        _("Line '%s' has no suspense account.") % (line.name or "")
                    )
                if line.amount <= 0:
                    raise ValidationError(
                        _("Line '%s' must have a positive amount.")
                        % (line.name or "")
                    )
            if not rec.partner_id:
                rec.partner_id = rec._default_partner_id()
            # snapshot if blank
            if not rec.customer_name and rec.partner_id:
                rec._onchange_partner_id()
            if rec.name == "/" or not rec.name:
                seq = rec._get_receipt_sequence(rec.department_id, rec.date)
                rec.name = seq.next_by_id()
            move = rec._create_issue_move()
            rec.move_id = move.id
            rec.state = "issued"
        return True

    def _create_issue_move(self):
        self.ensure_one()
        AccountMove = self.env["account.move"]
        cash_account = self.journal_id.default_account_id
        if not cash_account:
            raise UserError(
                _("Journal '%s' has no default account.") % self.journal_id.name
            )
        line_vals = [
            (
                0,
                0,
                {
                    "name": _("Receipt %s") % self.name,
                    "account_id": cash_account.id,
                    "debit": self.amount_total,
                    "credit": 0.0,
                    "partner_id": self.partner_id.id,
                    "currency_id": self.currency_id.id,
                },
            )
        ]
        for line in self.line_ids:
            line_vals.append(
                (
                    0,
                    0,
                    {
                        "name": line.name or self.name,
                        "account_id": line.suspense_account_id.id,
                        "debit": 0.0,
                        "credit": line.amount,
                        "partner_id": self.partner_id.id,
                        "currency_id": self.currency_id.id,
                        "analytic_distribution": line.analytic_distribution,
                    },
                )
            )
        move = AccountMove.create(
            {
                "ref": self.name,
                "date": self.date,
                "journal_id": self.journal_id.id,
                "company_id": self.company_id.id,
                "line_ids": line_vals,
            }
        )
        move.action_post()
        return move

    def action_open_cancel_wizard(self):
        self.ensure_one()
        if self.state != "issued":
            raise UserError(_("Only issued receipts can be cancelled."))
        if self.cash_deposit_id:
            raise UserError(
                _(
                    "This receipt has already been included in cash deposit %s. "
                    "Use Refund instead."
                )
                % self.cash_deposit_id.display_name
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Cancel Receipt"),
            "res_model": "receipt.kmitl.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_receipt_id": self.id},
        }

    def _apply_cancel(self, reason, user):
        self.ensure_one()
        if self.move_id and self.move_id.state == "posted":
            reverse = self.move_id._reverse_moves(
                default_values_list=[
                    {
                        "ref": _("Cancellation of %s") % self.name,
                        "date": fields.Date.context_today(self),
                    }
                ],
                cancel=False,
            )
            reverse.action_post()
        self.write(
            {
                "state": "cancelled",
                "cancel_reason": reason,
                "cancelled_by": user.id,
                "cancelled_date": fields.Datetime.now(),
            }
        )

    def action_open_refund_wizard(self):
        self.ensure_one()
        if self.state not in ("deposited", "reclassified"):
            raise UserError(
                _("Refund is for deposited or reclassified receipts. "
                  "Use Cancel for receipts not yet deposited.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Refund Receipt"),
            "res_model": "receipt.kmitl.refund.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_receipt_id": self.id},
        }

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Only draft receipts can be deleted. "
                      "Use Cancel for issued receipts.")
                )
        return super().unlink()
