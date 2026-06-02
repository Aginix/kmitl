# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class CashDeposit(models.Model):
    _name = "receipt.kmitl.cash.deposit"
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
            ("confirmed", "Confirmed"),
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
        "receipt.kmitl",
        "cash_deposit_id",
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
    system_amount = fields.Monetary(
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    physical_amount = fields.Monetary(
        string="Physical Amount Counted",
        currency_field="currency_id",
        help="Amount counted physically at central finance. "
             "Informational only — discrepancies must be reconciled via a "
             "manual journal entry by central finance.",
    )
    difference_amount = fields.Monetary(
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    note = fields.Text()
    confirmed_by = fields.Many2one("res.users", readonly=True, copy=False)
    confirmed_date = fields.Datetime(readonly=True, copy=False)

    @api.depends("receipt_ids.amount_total", "physical_amount")
    def _compute_amounts(self):
        for rec in self:
            rec.system_amount = sum(rec.receipt_ids.mapped("amount_total"))
            rec.difference_amount = (rec.physical_amount or 0.0) - rec.system_amount

    def _get_sequence(self):
        self.ensure_one()
        dept_code = (self.department_id.code or "00")
        ReceiptKmitl = self.env["receipt.kmitl"]
        fy_suffix = ReceiptKmitl._get_fiscal_year_suffix(self.date)
        seq_code = "receipt.kmitl.deposit.%s.%s" % (dept_code, fy_suffix)
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "Cash Deposit %s FY%s" % (dept_code, fy_suffix),
                    "code": seq_code,
                    "prefix": "CD/%s/%s/" % (dept_code, fy_suffix),
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    def action_pull_today_receipts(self):
        """Auto-bundle all cash receipts of the same department that are
        issued, paid by cash, and not yet linked to a deposit."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Can only pull receipts on draft deposits."))
            receipts = self.env["receipt.kmitl"].search(
                [
                    ("department_id", "=", rec.department_id.id),
                    ("payment_method", "=", "cash"),
                    ("state", "=", "issued"),
                    ("cash_deposit_id", "=", False),
                    ("date", "<=", rec.date),
                ]
            )
            if not receipts:
                raise UserError(
                    _("No pending cash receipts found for this department.")
                )
            # we set the back-ref through confirm; here just collect ids
            rec.write({"receipt_ids": [(6, 0, receipts.ids)]})

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft deposits can be confirmed."))
            if not rec.receipt_ids:
                raise ValidationError(_("Add at least one receipt to deposit."))
            for receipt in rec.receipt_ids:
                if receipt.state != "issued":
                    raise ValidationError(
                        _("Receipt %s is not in issued state.") % receipt.name
                    )
                if receipt.payment_method != "cash":
                    raise ValidationError(
                        _("Only cash receipts can be deposited; "
                          "%s uses %s.")
                        % (receipt.name, receipt.payment_method)
                    )
                if receipt.department_id != rec.department_id:
                    raise ValidationError(
                        _("Receipt %s belongs to a different department.")
                        % receipt.name
                    )
            if rec.name == "/" or not rec.name:
                rec.name = rec._get_sequence().next_by_id()
            rec.receipt_ids.write({"state": "deposited"})
            rec.write(
                {
                    "state": "confirmed",
                    "confirmed_by": self.env.user.id,
                    "confirmed_date": fields.Datetime.now(),
                }
            )

    def action_cancel(self):
        for rec in self:
            if rec.state == "confirmed":
                raise UserError(
                    _(
                        "Cannot cancel a confirmed deposit. "
                        "Create a manual JE adjustment instead."
                    )
                )
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(_("Only cancelled deposits can be reset to draft."))
            rec.state = "draft"

    def unlink(self):
        for rec in self:
            if rec.state == "confirmed":
                raise UserError(_("Confirmed deposits cannot be deleted."))
        return super().unlink()
