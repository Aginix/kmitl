# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ReceiptRemittance(models.Model):
    _name = "kmitl.receipt.remittance"
    _description = "KMITL Receipt Remittance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Remittance Number",
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
            ("done", "Done"),
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
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        required=True,
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    receipt_ids = fields.One2many(
        "kmitl.receipt",
        "remittance_id",
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
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
    )
    receipt_to_add_id = fields.Many2one(
        "kmitl.receipt",
        string="Add Receipt",
        domain="[('state', '=', 'confirmed'), ('remittance_id', '=', False),"
               " ('company_id', '=', company_id),"
               " ('department_analytic_id', 'child_of', department_analytic_id)]",
    )
    note = fields.Text()
    submitted_by = fields.Many2one("res.users", readonly=True, copy=False)
    submitted_date = fields.Datetime(readonly=True, copy=False)
    done_by = fields.Many2one("res.users", readonly=True, copy=False)
    done_date = fields.Datetime(readonly=True, copy=False)

    receipt_count = fields.Integer(
        compute="_compute_receipt_count",
        string="# Receipts",
    )

    @api.depends("receipt_ids")
    def _compute_receipt_count(self):
        for rec in self:
            rec.receipt_count = len(rec.receipt_ids)

    @api.onchange("receipt_to_add_id")
    def _onchange_receipt_to_add_id(self):
        if self.receipt_to_add_id:
            self.receipt_ids = [(4, self.receipt_to_add_id.id)]
            self.receipt_to_add_id = False

    @api.depends("receipt_ids.amount_total")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.receipt_ids.mapped("amount_total"))

    @api.onchange("date")
    def _onchange_date(self):
        if self.date:
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", self.date),
                    ("date_to", ">=", self.date),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if fiscal_year:
                self.account_fiscal_year_id = fiscal_year

    def _get_fy_be(self):
        self.ensure_one()
        if self.account_fiscal_year_id:
            return self.account_fiscal_year_id.date_to.year + 543
        return self.env["kmitl.receipt"]._get_fiscal_year_be(self.date)

    def _get_sequence(self):
        self.ensure_one()
        fy_be = self._get_fy_be()
        seq_code = "kmitl.receipt.remittance.%s" % fy_be
        IrSeq = self.env["ir.sequence"].sudo()
        seq = IrSeq.search([("code", "=", seq_code)], limit=1)
        if not seq:
            seq = IrSeq.create(
                {
                    "name": "Receipt Remittance FY%s" % fy_be,
                    "code": seq_code,
                    "prefix": "RM/%s/" % fy_be,
                    "padding": 4,
                    "company_id": False,
                }
            )
        return seq

    def action_pull_pending_receipts(self):
        """Bundle confirmed, unremitted receipts from the department's whole
        subtree (the remittance department may be a parent/rollup unit)."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Can only pull receipts on draft remittances."))
            receipts = self.env["kmitl.receipt"].search(
                [
                    ("company_id", "=", rec.company_id.id),
                    (
                        "department_analytic_id",
                        "child_of",
                        rec.department_analytic_id.id,
                    ),
                    ("state", "=", "confirmed"),
                    ("remittance_id", "=", False),
                    ("date", "<=", rec.date),
                ]
            )
            if not receipts:
                raise UserError(
                    _("No pending confirmed receipts found for this department.")
                )
            rec.write({"receipt_ids": [(6, 0, receipts.ids)]})

    def action_submit(self):
        """Department submits the remittance to central treasury."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft remittances can be submitted."))
            if not rec.receipt_ids:
                raise ValidationError(_("Add at least one receipt before submitting."))
            for receipt in rec.receipt_ids:
                if receipt.state != "confirmed":
                    raise ValidationError(
                        _("Receipt %s must be confirmed.") % receipt.name
                    )
                if not self.env["account.analytic.account"].search_count(
                    [
                        ("id", "=", receipt.department_analytic_id.id),
                        ("id", "child_of", rec.department_analytic_id.id),
                    ]
                ):
                    raise ValidationError(
                        _("Receipt %s does not belong to this department's subtree.")
                        % receipt.name
                    )
                if receipt.company_id != rec.company_id:
                    raise ValidationError(
                        _("Receipt %s belongs to a different company.")
                        % receipt.name
                    )
                if receipt.currency_id != rec.currency_id:
                    raise ValidationError(
                        _("Receipt %s uses a different currency than the "
                          "remittance.") % receipt.name
                    )
            rec.date = fields.Date.context_today(rec)
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", rec.date),
                    ("date_to", ">=", rec.date),
                    ("company_id", "=", rec.company_id.id),
                ],
                limit=1,
            )
            if fiscal_year:
                rec.account_fiscal_year_id = fiscal_year
            if rec.name == "/" or not rec.name:
                rec.name = rec._get_sequence().next_by_id()
            rec.write(
                {
                    "state": "submitted",
                    "submitted_by": self.env.user.id,
                    "submitted_date": fields.Datetime.now(),
                }
            )

    def action_done(self):
        """Central treasury reviews and posts: every remaining receipt gets
        its own journal entry (Dr payment-method account / Cr income)."""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted remittances can be posted."))
            if not rec.receipt_ids:
                raise UserError(
                    _("Cannot post a remittance with no receipts. "
                      "All receipts have been detached.")
                )
            for receipt in rec.receipt_ids:
                if receipt.state != "confirmed":
                    raise ValidationError(
                        _("Receipt %s is not in confirmed state.") % receipt.name
                    )
            rec.receipt_ids.action_post()
            rec.write(
                {
                    "state": "done",
                    "done_by": self.env.user.id,
                    "done_date": fields.Datetime.now(),
                }
            )

    def action_recall(self):
        """Creator recalls a submitted remittance back to draft."""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(
                    _("Only submitted remittances can be recalled.")
                )
            if rec.submitted_by != self.env.user:
                raise UserError(
                    _("Only the person who submitted this remittance can recall it.")
                )
            rec.message_post(
                body=_("Remittance recalled by %s.") % self.env.user.name
            )
            rec.write(
                {
                    "state": "draft",
                    "submitted_by": False,
                    "submitted_date": False,
                }
            )

    def action_reject(self):
        """Treasury officer opens the reject wizard to provide a reason."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Remittance"),
            "res_model": "kmitl.receipt.remittance.reject",
            "view_mode": "form",
            "target": "new",
            "context": {"default_remittance_id": self.id},
        }

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("Done remittances cannot be cancelled."))
            rec.receipt_ids.write({"remittance_id": False})
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(_("Only cancelled remittances can reset to draft."))
            rec.write(
                {
                    "state": "draft",
                    "submitted_by": False,
                    "submitted_date": False,
                }
            )

    def unlink(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("Done remittances cannot be deleted."))
        return super().unlink()
