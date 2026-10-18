# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.receipt_kmitl.models.receipt_kmitl import ANALYTIC_KEYS

# Fields readonly from the moment the invoice leaves draft: a submission drives it
# from there on.
READONLY_STATES = {
    "submitted": [("readonly", True)],
    "accepted": [("readonly", True)],
    "issued": [("readonly", True)],
    "paid": [("readonly", True)],
    "cancelled": [("readonly", True)],
}

# The dimensions the accounting office's own form demands on every journal entry
# (accounting_kmitl): an invoice without all four could not be submitted there.
REQUIRED_DIMENSIONS = (
    "department_analytic_id",
    "source_analytic_id",
    "fund_analytic_id",
    "activity_analytic_id",
)


class InvoiceKmitl(models.Model):
    _name = "kmitl.invoice"
    _description = "KMITL Invoice"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _order = "date desc, id desc"
    _analytic_keys = ANALYTIC_KEYS

    name = fields.Char(
        string="Invoice Number",
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
            ("accepted", "Accepted"),
            ("issued", "Issued"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
        help="Where the invoice stands for the department. 'Paid' means the "
        "department took the money and issued the receipt; whether the books show "
        "the debt settled is the Accounting Payment Status.",
    )
    date = fields.Date(
        string="Invoice Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        states=READONLY_STATES,
    )
    date_due = fields.Date(
        string="Due Date",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )

    # --- Analytic dimensions (header-level, synced to lines) ---
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Issuing Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=True,
        index=True,
        required=True,
        # A stored computed field is not copied by default, and duplicate would
        # leave this empty and trip the required check.
        copy=True,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=True,
        required=True,
        copy=True,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=True,
        required=True,
        copy=True,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=True,
        required=True,
        copy=True,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="KMITL Project",
        compute="_compute_analytic_id",
        inverse="_inverse_kmitl_project_analytic",
        domain=[("root_plan_id.code", "=", "kmitl_project")],
        store=False,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Procurement Plan",
        compute="_compute_analytic_id",
        inverse="_inverse_procurement_plan_analytic",
        domain=[("root_plan_id.code", "=", "procurement_plan")],
        store=False,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )

    line_ids = fields.One2many(
        "kmitl.invoice.line",
        "invoice_id",
        string="Lines",
        copy=True,
        states=READONLY_STATES,
    )
    note = fields.Text(string="Notes")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        states=READONLY_STATES,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Issued By",
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True,
        copy=False,
    )

    # --- What the invoice has led to ---
    submission_id = fields.Many2one(
        "kmitl.invoice.submission",
        string="Invoice Submission",
        readonly=True,
        copy=False,
        index=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Receivable Entry",
        readonly=True,
        copy=False,
        help="The customer invoice (ใบตั้งหนี้) the accounting office books for this "
        "invoice.",
    )
    refund_move_id = fields.Many2one(
        "account.move",
        string="Credit Note",
        readonly=True,
        copy=False,
        help="The credit note that reverses the receivable entry when the invoice is "
        "cancelled after the accounting office posted it.",
    )
    receipt_id = fields.Many2one(
        "kmitl.receipt",
        string="Receipt",
        readonly=True,
        copy=False,
    )
    # The books' side of the invoice. Related fields read as superuser, so a
    # department user sees them without any access to the accounting entry.
    payment_state = fields.Selection(
        related="move_id.payment_state",
        string="Accounting Payment Status",
        readonly=True,
    )
    amount_residual = fields.Monetary(
        related="move_id.amount_residual",
        string="Amount Due (Accounting)",
        currency_field="currency_id",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------------
    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped("amount"))

    # -------------------------------------------------------------------------
    # Analytic dimension sync (header → lines)
    # -------------------------------------------------------------------------
    @api.depends("analytic_distribution")
    def _compute_analytic_id(self):
        # Reset first: the shared mixin only assigns the dimensions present in the
        # JSON, so a dimension removed from it would keep its stale value.
        for rec in self:
            for field_name in self._analytic_keys.values():
                rec[field_name] = False
        return super()._compute_analytic_id()

    # Also onchange handlers: on an unsaved record the inverse only runs at
    # write(). Each must stay single-field — looping over all six codes would
    # reassign analytic_distribution after the first, invalidating every
    # dimension field (they share one compute) and wiping the one just edited.
    @api.onchange("department_analytic_id")
    def _inverse_department_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("departments")

    @api.onchange("source_analytic_id")
    def _inverse_source_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("sources")

    @api.onchange("fund_analytic_id")
    def _inverse_fund_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("funds")

    @api.onchange("activity_analytic_id")
    def _inverse_activity_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("activities")

    @api.onchange("kmitl_project_analytic_id")
    def _inverse_kmitl_project_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("kmitl_project")

    @api.onchange("procurement_plan_analytic_id")
    def _inverse_procurement_plan_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("procurement_plan")

    def _sync_analytic_to_lines(self):
        for rec in self:
            if rec.line_ids:
                rec.line_ids.write({"analytic_distribution": rec.analytic_distribution})

    # A write touching any of these must re-push the header distribution onto the
    # lines: the dimension fields, the JSON itself, and line_ids (a new line
    # starts with no distribution).
    _SYNC_TRIGGERS = frozenset(ANALYTIC_KEYS.values()) | {
        "analytic_distribution",
        "line_ids",
    }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_analytic_to_lines()
        for rec in records:
            if rec.name in ("/", False):
                rec.name = rec._get_sequence(rec.date).next_by_id()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self._SYNC_TRIGGERS & set(vals):
            self._sync_analytic_to_lines()
        return res

    # -------------------------------------------------------------------------
    # Sequence
    # -------------------------------------------------------------------------
    @api.model
    def _get_fiscal_year_sequence(self, code, name, prefix, date):
        """The ``no_gap`` sequence ``<code>.<fiscal year>`` of ``date``, created on
        first use (``hooks.post_init_hook`` creates the coming years in advance)."""
        fy_be = self.env["kmitl.receipt"]._get_fiscal_year_be(date)
        seq_code = "%s.%s" % (code, fy_be)
        IrSequence = self.env["ir.sequence"].sudo()
        sequence = IrSequence.search([("code", "=", seq_code)], limit=1)
        return sequence or IrSequence.create(
            {
                "name": "%s FY%s" % (name, fy_be),
                "code": seq_code,
                "prefix": "%s/%s/" % (prefix, fy_be),
                "padding": 4,
                "implementation": "no_gap",
                "company_id": False,
            }
        )

    @api.model
    def _get_sequence(self, date):
        return self._get_fiscal_year_sequence("kmitl.invoice", "Invoice", "IV", date)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains("line_ids", "amount_total")
    def _check_lines(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_("Add at least one line."))
            for line in rec.line_ids:
                if not line.account_id:
                    raise ValidationError(
                        _("Line '%s' has no income account.") % (line.name or "")
                    )
            if rec.amount_total <= 0:
                raise ValidationError(_("The invoice total must be greater than zero."))

    @api.constrains("date", "date_due")
    def _check_date_due(self):
        for rec in self:
            if rec.date_due < rec.date:
                raise ValidationError(
                    _("The due date cannot be earlier than the invoice date.")
                )

    # -------------------------------------------------------------------------
    # The receivable entry (ใบตั้งหนี้)
    # -------------------------------------------------------------------------
    def _prepare_move_vals(self):
        self.ensure_one()
        return {
            "move_type": "out_invoice",
            "journal_id": self.env.ref("account_kmitl.journal_ar").id,
            "partner_id": self.partner_id.id,
            # Left out, core stamps the day the entry is posted: the debt would be
            # raised on the wrong date.
            "invoice_date": self.date,
            "invoice_date_due": self.date_due,
            # A multi-instalment term would split the receivable into several lines
            # and overwrite the due date.
            "invoice_payment_term_id": False,
            "ref": self.name,
            "company_id": self.company_id.id,
            "kmitl_invoice_id": self.id,
            "analytic_distribution": self.analytic_distribution,
            "invoice_line_ids": [
                Command.create(self._prepare_move_line_vals(line))
                for line in self.line_ids
            ],
        }

    def _prepare_move_line_vals(self, line):
        self.ensure_one()
        return {
            "name": line.name,
            "product_id": line.product_id.id,
            "account_id": line.account_id.id,
            "quantity": line.quantity,
            "price_unit": line.price_unit,
            # KMITL charges no VAT. Cleared on purpose: a sale tax later put on the
            # product would otherwise attach to the invoice without a word.
            "tax_ids": [Command.clear()],
            "analytic_distribution": line.analytic_distribution,
        }

    def _create_move(self):
        """Raise the receivable entry: a draft ``out_invoice`` the accounting office
        submits and approves like any other entry."""
        self.ensure_one()
        partner = self.partner_id.with_company(self.company_id)
        if not partner.property_account_receivable_id:
            raise UserError(
                _("Partner '%s' has no receivable account. Set its partner type first.")
                % partner.display_name
            )
        self.move_id = self.env["account.move"].create(self._prepare_move_vals())

    def _get_receivable_account(self):
        """The receivable account the invoice's own entry was booked to.

        Read back from the entry, never derived from the partner again: re-typing a
        partner re-stamps its receivable account, and a receipt crediting another
        account could not be reconciled with the invoice. Read as superuser, because
        the entry may sit in an operating unit the reader cannot see.
        """
        self.ensure_one()
        invoice = self.sudo()
        account = invoice.move_id.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        ).account_id
        if not account:
            raise UserError(_("Invoice %s has no receivable entry.") % invoice.name)
        return account

    # -------------------------------------------------------------------------
    # Reconciliation (the books' side of "paid")
    # -------------------------------------------------------------------------
    def _get_settling_move(self):
        """The entry that settles the invoice's receivable: the receipt's, or the
        credit note's once the invoice is cancelled."""
        self.ensure_one()
        if self.state == "cancelled":
            return self.refund_move_id
        return self.receipt_id.move_id

    def _get_reconcile_lines(self):
        """Open receivable lines of the invoice entry and of the entry settling it,
        none while either is not posted yet.

        Looked up and read as superuser: an operating unit's read rule would hide
        the counterpart from a user outside it, and the reconciliation would be
        skipped without a word. The receipt credits the receivable once per receipt
        line against the invoice's single debit, so this is N lines to one.
        """
        self.ensure_one()
        invoice = self.sudo()
        moves = invoice.move_id | invoice._get_settling_move()
        if len(moves) < 2 or any(move.state != "posted" for move in moves):
            return invoice.env["account.move.line"]
        account = invoice._get_receivable_account()
        return moves.line_ids.filtered(
            lambda line: line.account_id == account and not line.reconciled
        )

    def _reconcile(self):
        """Reconcile what can be reconciled; the lines done (none when not ready)."""
        lines = self._get_reconcile_lines()
        lines.reconcile()
        return lines

    def _auto_reconcile(self):
        """Reconcile once either entry is posted, a refusal becoming a note on the
        invoice rather than a failed posting: whoever posts is not the one who can
        mend an invoice."""
        for invoice in self:
            try:
                with self.env.cr.savepoint():
                    invoice._reconcile()
            except UserError as error:
                invoice.sudo().message_post(
                    body=_("Automatic reconciliation skipped: %s") % error.args[0]
                )

    def action_reconcile(self):
        self.ensure_one()
        if not self._reconcile():
            raise UserError(
                _(
                    "Nothing to reconcile yet: the invoice entry and the entry "
                    "settling it must both be posted."
                )
            )
        return True

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def _prepare_receipt_vals(self):
        """Values of the draft receipt that collects the invoice in full."""
        self.ensure_one()
        method = self.env["kmitl.payment.method"].search(
            [("payment_type", "=", "cash"), ("company_id", "=", self.company_id.id)],
            order="sequence, id",
            limit=1,
        )
        if not method:
            raise UserError(_("No cash payment method is configured."))
        # Every dimension is stated, not only the JSON: the receipt's source carries
        # a default that its inverse would otherwise write over the invoice's own,
        # and the stored ones are NOT NULL at INSERT.
        vals = {name: self[name].id for name in REQUIRED_DIMENSIONS}
        vals.update(
            {
                "invoice_id": self.id,
                "company_id": self.company_id.id,
                "partner_id": self.partner_id.id,
                # Left on, the form's walk-in onchange swaps the partner back out.
                "is_walkin": False,
                "description": _("Payment of invoice %s") % self.name,
                "payment_type": "cash",
                "payment_method_id": method.id,
                "analytic_distribution": self.analytic_distribution,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": line.product_id.id,
                            "name": line.name,
                            "account_id": line.account_id.id,
                            "quantity": line.quantity,
                            "price_unit": line.price_unit,
                        }
                    )
                    for line in self.line_ids
                ],
            }
        )
        return vals

    def action_receive_payment(self):
        """The debtor pays: draft the receipt and mark the invoice paid at once.

        'Paid' here is the department's: money taken, receipt issued. The books
        settle the debt later, when the receipt's entry is posted.
        """
        self.ensure_one()
        if self.state != "issued":
            raise UserError(_("Only an issued invoice can be paid."))
        # The accounting office can delete or cancel a draft entry on its own side.
        # Read as superuser: a department user has no right on account.move.
        if self.sudo().move_id.state in (False, "cancel"):
            raise UserError(
                _(
                    "The receivable entry of invoice %s was deleted or cancelled in "
                    "accounting, so there is nothing to settle. Ask the treasury "
                    "office to cancel the invoice and issue a new one."
                )
                % self.name
            )
        receipt = self.env["kmitl.receipt"].create(self._prepare_receipt_vals())
        receipt._sync_customer_snapshot()
        self.write({"state": "paid", "receipt_id": receipt.id})
        return self._open_form(receipt)

    def action_cancel(self):
        for rec in self:
            if rec.state == "draft":
                submission = rec.submission_id
                rec.write({"submission_id": False, "state": "cancelled"})
                if submission:
                    rec.message_post(
                        body=_("Cancelled and removed from submission %s.")
                        % submission.display_name
                    )
                    submission.message_post(
                        body=_(
                            "Invoice %s was cancelled and removed from this "
                            "submission."
                        )
                        % rec.name
                    )
            elif rec.state == "issued":
                rec._cancel_issued()
            elif rec.state == "paid":
                raise UserError(
                    _(
                        "Invoice %(invoice)s is paid. Cancel its receipt "
                        "%(receipt)s first."
                    )
                    % {"invoice": rec.name, "receipt": rec.receipt_id.display_name}
                )
            else:
                raise UserError(
                    _("Invoice %s cannot be cancelled in its current state.")
                    % rec.name
                )
        return True

    def _prepare_refund_vals(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return {
            "ref": _("Reversal of: %s") % self.name,
            "date": today,
            "invoice_date": today,
            "invoice_date_due": today,
            "invoice_payment_term_id": False,
            "kmitl_invoice_id": self.id,
        }

    def _cancel_issued(self):
        """Cancel an issued invoice: the whole of it, as issued by mistake.

        Whatever the accounting office has done with the receivable entry decides
        how it is undone: a draft is deleted, a posted one is reversed by a draft
        credit note that goes through the same approval, and one under review is
        theirs to send back first.
        """
        self.ensure_one()
        if not self.env.user.has_group("invoice_kmitl.group_invoice_kmitl_approver"):
            raise UserError(_("Only the treasury office can cancel an issued invoice."))
        move = self.move_id
        if move.state == "posted":
            self.refund_move_id = move._reverse_moves([self._prepare_refund_vals()])
        elif move.state == "submitted":
            raise UserError(
                _(
                    "Entry %s is awaiting approval in accounting. Ask them to reset "
                    "it to draft first."
                )
                % move.display_name
            )
        else:
            # A draft entry, or none: deleted outright. The treasury office holds
            # no accounting-manager right, so force_delete stands in for it.
            move.with_context(force_delete=True).unlink()
        self.state = "cancelled"

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------
    @staticmethod
    def _open_form(record):
        return {
            "type": "ir.actions.act_window",
            "res_model": record._name,
            "res_id": record.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_view_move(self):
        self.ensure_one()
        return self._open_form(self.move_id)

    def action_view_refund(self):
        self.ensure_one()
        return self._open_form(self.refund_move_id)

    def action_view_receipt(self):
        self.ensure_one()
        return self._open_form(self.receipt_id)

    def action_view_submission(self):
        self.ensure_one()
        return self._open_form(self.submission_id)
