# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SuspenseAllocation(models.Model):
    _name = "receipt.kmitl.allocation"
    _description = "Suspense Allocation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Allocation Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
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
    note = fields.Text()
    line_ids = fields.One2many(
        "receipt.kmitl.allocation.line",
        "allocation_id",
        string="Lines",
        copy=True,
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
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain=[("type", "=", "general")],
        help="Miscellaneous journal used to post the reclassification entry.",
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("amount"))

    def _get_sequence(self):
        self.ensure_one()
        ReceiptKmitl = self.env["receipt.kmitl"]
        fy_suffix = ReceiptKmitl._get_fiscal_year_suffix(self.date)
        seq_code = "receipt.kmitl.allocation.%s" % fy_suffix
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "Suspense Allocation FY%s" % fy_suffix,
                    "code": seq_code,
                    "prefix": "SA/%s/" % fy_suffix,
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    def action_post(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft allocations can be posted."))
            if not rec.line_ids:
                raise ValidationError(_("Add at least one line."))
            for line in rec.line_ids:
                if not line.income_account_id:
                    raise ValidationError(
                        _("Line for receipt %s has no income account.")
                        % line.receipt_line_id.receipt_id.name
                    )
            if rec.name == "/" or not rec.name:
                rec.name = rec._get_sequence().next_by_id()
            move = rec._create_reclass_move()
            rec.move_id = move.id
            rec.state = "posted"
            # propagate state on impacted receipts when all lines allocated
            impacted = rec.line_ids.mapped("receipt_line_id.receipt_id")
            for receipt in impacted:
                pending = receipt.line_ids.filtered(
                    lambda l: not l.allocation_line_id
                )
                if not pending and receipt.state == "deposited":
                    receipt.state = "reclassified"

    def _create_reclass_move(self):
        self.ensure_one()
        move_lines = []
        for line in self.line_ids:
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": _("Reclass %s — %s")
                        % (
                            line.receipt_line_id.receipt_id.name,
                            line.receipt_line_id.name or "",
                        ),
                        "account_id": line.suspense_account_id.id,
                        "debit": line.amount,
                        "credit": 0.0,
                        "partner_id": line.receipt_line_id.receipt_id.partner_id.id,
                        "currency_id": self.currency_id.id,
                        "analytic_distribution": line.analytic_distribution,
                    },
                )
            )
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": _("Reclass %s — %s")
                        % (
                            line.receipt_line_id.receipt_id.name,
                            line.receipt_line_id.name or "",
                        ),
                        "account_id": line.income_account_id.id,
                        "debit": 0.0,
                        "credit": line.amount,
                        "partner_id": line.receipt_line_id.receipt_id.partner_id.id,
                        "currency_id": self.currency_id.id,
                        "analytic_distribution": line.analytic_distribution,
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
        # link allocation_line back to receipt_line
        for line in self.line_ids:
            line.receipt_line_id.allocation_line_id = line.id
        return move

    def action_cancel(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(
                    _(
                        "Posted allocations cannot be cancelled directly. "
                        "Reverse the journal entry manually if needed."
                    )
                )
            rec.state = "cancelled"

    def unlink(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Posted allocations cannot be deleted."))
        return super().unlink()
