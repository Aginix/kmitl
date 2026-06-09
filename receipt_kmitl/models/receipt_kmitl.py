# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ReceiptKmitl(models.Model):
    _name = "kmitl.receipt"
    _description = "KMITL Cash Receipt"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "posted": [("readonly", True)],
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
            ("confirmed", "Confirmed"),
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
    payment_method_id = fields.Many2one(
        "kmitl.payment.method",
        string="Payment Method",
        required=True,
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
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
        "kmitl.receipt.line",
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
    deposit_id = fields.Many2one(
        "kmitl.cash.deposit",
        string="Cash Deposit",
        readonly=True,
        copy=False,
    )
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
        walkin = self.env.ref(
            "receipt_kmitl.partner_walkin", raise_if_not_found=False
        )
        return walkin.id if walkin else False

    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("amount"))

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        self._sync_customer_snapshot()

    def _sync_customer_snapshot(self):
        """Copy the partner's identity onto the receipt snapshot fields so the
        printed receipt stays stable even if the partner record changes later."""
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
            if hasattr(partner, "branch") and partner.branch:
                rec.customer_branch_code = partner.branch

    # -------------------------------------------------------------------------
    # Sequence
    # -------------------------------------------------------------------------
    def _get_fiscal_year_be(self, date):
        """Thai fiscal year as the full Buddhist Era budget year.
        FY runs Oct → Sep, so Oct-Dec belong to the next budget year
        (e.g. 2025-10 → 2569)."""
        budget_year_ce = date.year + (1 if date.month >= 10 else 0)
        return budget_year_ce + 543

    def _get_fiscal_year_suffix(self, date):
        """2-digit Buddhist Era fiscal year for display (e.g. 2025-10 → '69')."""
        return str(self._get_fiscal_year_be(date))[-2:]

    def _get_or_create_dept_fy_sequence(
        self, department, date, code_ns, name_label, number_prefix
    ):
        """Lazy-create a per-(dept_code, fiscal_year) ir.sequence.

        The lookup ``code`` uses the full BE year so it never collides across
        century rollovers, while the human-facing ``prefix`` keeps the 2-digit
        year (e.g. ``RC/01/69/0001``)."""
        dept_code = department.code or "00"
        fy_be = self._get_fiscal_year_be(date)
        fy_suffix = str(fy_be)[-2:]
        seq_code = "%s.%s.%s" % (code_ns, dept_code, fy_be)
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "%s %s FY%s" % (name_label, dept_code, fy_suffix),
                    "code": seq_code,
                    "prefix": "%s/%s/%s/" % (number_prefix, dept_code, fy_suffix),
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    def _get_receipt_sequence(self, department, date):
        return self._get_or_create_dept_fy_sequence(
            department, date, "kmitl.receipt", "Receipt", "RC"
        )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_confirm(self):
        """Issued by the department: validate, assign number, allow printing.
        No journal entry is created here — central finance posts later."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft receipts can be confirmed."))
            if not rec.line_ids:
                raise ValidationError(_("Add at least one line before confirming."))
            for line in rec.line_ids:
                if not line.account_id:
                    raise ValidationError(
                        _("Line '%s' has no income account.") % (line.name or "")
                    )
                if line.amount <= 0:
                    raise ValidationError(
                        _("Line '%s' must have a positive amount.")
                        % (line.name or "")
                    )
            if not rec.partner_id:
                rec.partner_id = rec._default_partner_id()
            if not rec.customer_name and rec.partner_id:
                rec._sync_customer_snapshot()
            if rec.name == "/" or not rec.name:
                seq = rec._get_receipt_sequence(rec.department_id, rec.date)
                rec.name = seq.next_by_id()
            rec.state = "confirmed"
        return True

    def action_post(self):
        """Posted by central finance (typically via a cash deposit batch).
        Creates the journal entry: Dr payment-method account / Cr income."""
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(
                    _("Only confirmed receipts can be posted (%s).") % rec.name
                )
            move = rec._create_move()
            rec.move_id = move.id
            rec.state = "posted"
        return True

    def _create_move(self):
        self.ensure_one()
        method = self.payment_method_id
        if not method.account_id:
            raise UserError(
                _("Payment method '%s' has no debit account.") % method.name
            )
        line_vals = [
            (
                0,
                0,
                {
                    "name": _("Receipt %s") % self.name,
                    "account_id": method.account_id.id,
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
                        "account_id": line.account_id.id,
                        "debit": 0.0,
                        "credit": line.amount,
                        "partner_id": self.partner_id.id,
                        "currency_id": self.currency_id.id,
                        "analytic_distribution": line.analytic_distribution,
                    },
                )
            )
        move = self.env["account.move"].create(
            {
                "ref": self.name,
                "date": self.date,
                "journal_id": method.journal_id.id,
                "company_id": self.company_id.id,
                "line_ids": line_vals,
            }
        )
        move.action_post()
        return move

    def action_cancel(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(
                    _("Posted receipts cannot be cancelled. Use a reversal/credit "
                      "note from Accounting.")
                )
            if rec.deposit_id:
                raise UserError(
                    _("Receipt %s is in cash deposit %s; remove it from the deposit "
                      "first.") % (rec.name, rec.deposit_id.display_name)
                )
            rec.state = "cancelled"
        return True

    def action_draft(self):
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(_("Only cancelled receipts can be reset to draft."))
            rec.state = "draft"
        return True

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "cancelled"):
                raise UserError(
                    _("Only draft or cancelled receipts can be deleted.")
                )
        return super().unlink()
