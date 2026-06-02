# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ReceiptRefund(models.Model):
    _name = "receipt.kmitl.refund"
    _description = "Receipt Refund"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Refund Number",
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
    receipt_id = fields.Many2one(
        "receipt.kmitl",
        string="Receipt",
        required=True,
        domain="[('state', 'in', ['deposited', 'reclassified'])]",
        tracking=True,
    )
    department_id = fields.Many2one(
        related="receipt_id.department_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related="receipt_id.partner_id",
        store=True,
        readonly=True,
    )
    refund_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("transfer", "Bank Transfer"),
        ],
        required=True,
        default="cash",
        tracking=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Refund Journal",
        required=True,
        domain="[('type', 'in', ['cash', 'bank'])]",
        help="Journal used for the refund payment (Cr Cash/Bank).",
    )
    reason = fields.Text(required=True)
    line_ids = fields.One2many(
        "receipt.kmitl.refund.line",
        "refund_id",
        string="Refund Lines",
        copy=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="receipt_id.currency_id",
        store=True,
        readonly=True,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )

    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("amount"))

    def _get_sequence(self):
        self.ensure_one()
        ReceiptKmitl = self.env["receipt.kmitl"]
        fy_suffix = ReceiptKmitl._get_fiscal_year_suffix(self.date)
        seq_code = "receipt.kmitl.refund.%s" % fy_suffix
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "Receipt Refund FY%s" % fy_suffix,
                    "code": seq_code,
                    "prefix": "RF/%s/" % fy_suffix,
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft refunds can be submitted."))
            if not rec.line_ids:
                raise ValidationError(_("Add at least one refund line."))
            if rec.name == "/" or not rec.name:
                rec.name = rec._get_sequence().next_by_id()
            rec.state = "submitted"

    def action_post(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted refunds can be posted."))
            for line in rec.line_ids:
                if line.amount <= 0:
                    raise ValidationError(
                        _("Line amounts must be positive.")
                    )
                if line.amount > line.receipt_line_id.amount:
                    raise ValidationError(
                        _(
                            "Refund amount for line '%s' exceeds the original "
                            "receipt line amount."
                        )
                        % (line.receipt_line_id.name or "")
                    )
            move = rec._create_refund_move()
            rec.move_id = move.id
            rec.state = "posted"

    def _refund_debit_account(self, receipt_line):
        """If the receipt line has been reclassified, the debit goes to the
        income account already used in the allocation. Otherwise it goes
        to the suspense account."""
        if receipt_line.allocation_line_id:
            return receipt_line.allocation_line_id.income_account_id
        return receipt_line.suspense_account_id

    def _create_refund_move(self):
        self.ensure_one()
        cash_account = self.journal_id.default_account_id
        if not cash_account:
            raise UserError(
                _("Refund journal '%s' has no default account.") % self.journal_id.name
            )
        move_lines = []
        for line in self.line_ids:
            debit_account = self._refund_debit_account(line.receipt_line_id)
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": _("Refund %s — %s")
                        % (self.name, line.receipt_line_id.name or ""),
                        "account_id": debit_account.id,
                        "debit": line.amount,
                        "credit": 0.0,
                        "partner_id": self.partner_id.id,
                        "currency_id": self.currency_id.id,
                        "analytic_distribution": line.receipt_line_id.analytic_distribution,
                    },
                )
            )
        move_lines.append(
            (
                0,
                0,
                {
                    "name": _("Refund %s") % self.name,
                    "account_id": cash_account.id,
                    "debit": 0.0,
                    "credit": self.amount_total,
                    "partner_id": self.partner_id.id,
                    "currency_id": self.currency_id.id,
                },
            )
        )
        move = self.env["account.move"].create(
            {
                "ref": self.name,
                "date": self.date,
                "journal_id": self.journal_id.id,
                "company_id": self.company_id.id,
                "line_ids": move_lines,
            }
        )
        move.action_post()
        return move

    def action_cancel(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(
                    _("Posted refunds cannot be cancelled. Use a reverse JE.")
                )
            rec.state = "cancelled"

    def unlink(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Posted refunds cannot be deleted."))
        return super().unlink()
