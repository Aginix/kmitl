# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    kmitl_payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Operation Type",
        required=True,
    )
    to_reconcile_payment_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_payment_to_reconcile_line_rel",
        column1="payment_id",
        column2="move_line_id",
        string="Lines to Reconcile",
        copy=False,
    )
    amount_wht = fields.Monetary(
        string="Withholding Tax",
        compute="_compute_amount_wht",
        currency_field="currency_id",
        help="Total withholding tax withheld on this payment. Derived from the "
        "payment move lines carrying a WHT tax, so it is visible in every state "
        "(the native withholding moves are only created on posting).",
    )
    amount_before_wht = fields.Monetary(
        string="Amount Before Withholding",
        compute="_compute_amount_wht",
        currency_field="currency_id",
        help="Gross amount before withholding tax (net amount paid plus the "
        "withholding tax).",
    )

    bank_result_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="Bank Result",
        copy=False,
        tracking=True,
        help="Result reported by the bank for this outbound e-payment. Set "
        "from the bank payment export line once the bank confirms the "
        "transfer succeeded or failed. Cheque payments are confirmed manually "
        "by the finance office instead.",
    )
    is_cheque_payment = fields.Boolean(
        string="Is Cheque Payment",
        compute="_compute_is_cheque_payment",
    )

    @api.depends("payment_method_line_id.payment_method_id.code")
    def _compute_is_cheque_payment(self):
        for payment in self:
            payment.is_cheque_payment = (
                payment.payment_method_line_id.payment_method_id.code
                == "kmitl_cheque"
            )

    # หัวจ่าย is ``payment_method_line_id``: the money side of the entry is that
    # line's own payment_account_id, which core already reads and already counts
    # as a valid liquidity account. Nothing to override — KMITL simply never
    # reconciles a bank statement afterwards, so what Odoo calls the outstanding
    # account is the final one here.

    def action_mark_bank_result_success(self):
        """Finance manually confirms a cheque payment was actually paid.

        Transfers are confirmed from the bank payment export line instead
        (which also logs the e-payment result); this manual path exists for
        cheques, which never enter a bank export.
        """
        self.write({"bank_result_status": "success"})

    def action_mark_bank_result_failed(self):
        self.write({"bank_result_status": "failed"})

    cheque_register_ids = fields.One2many(
        comodel_name="cheque.register",
        inverse_name="payment_id",
        string="Cheques",
    )
    cheque_register_count = fields.Integer(
        compute="_compute_cheque_register_count",
    )

    @api.depends("move_id.line_ids.wht_tax_id", "move_id.line_ids.balance", "amount")
    def _compute_amount_wht(self):
        for payment in self:
            wht_lines = payment.move_id.line_ids.filtered("wht_tax_id")
            payment.amount_wht = sum(abs(line.balance) for line in wht_lines)
            payment.amount_before_wht = payment.amount + payment.amount_wht

    @api.depends("cheque_register_ids")
    def _compute_cheque_register_count(self):
        for payment in self:
            payment.cheque_register_count = len(payment.cheque_register_ids)

    def _needs_bank_export(self):
        """Only an outbound bank transfer travels in an e-payment file.

        Cheques are handed over and cash is paid at the counter, so neither can
        ever gain an export and neither may be held back by the export gate.
        """
        self.ensure_one()
        # Keyed off the paying account's own method: it is what the officer
        # picked, so it cannot disagree with how the money actually leaves.
        code = self.payment_method_line_id.payment_method_id.code
        if code in ("kmitl_cheque", "kmitl_cash"):
            return False
        return self.payment_type == "outbound"

    def action_post(self):
        """Validate bank export for outbound, then reconcile after posting."""
        for payment in self:
            if payment._needs_bank_export() and payment.export_status == "draft":
                raise UserError(
                    _("Payment must be exported to bank before posting.")
                )
        res = super().action_post()
        self._reconcile_source_invoice_lines()
        self._create_cheque_register_entries()
        return res

    def _create_cheque_register_entries(self):
        """Add a cheque to the control register when a cheque-type payment posts.

        The row is created in ``draft`` because the physical cheque number is
        entered by the finance officer, who then issues it from the register.
        """
        for payment in self.filtered(
            lambda p: p.is_cheque_payment and not p.cheque_register_ids
        ):
            self.env["cheque.register"].create(
                payment._prepare_cheque_register_vals()
            )

    def _prepare_cheque_register_vals(self):
        self.ensure_one()
        return {
            "direction": self.payment_type,
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "journal_id": self.journal_id.id,
            "paying_account_id": self.payment_method_line_id.id,
            "cheque_date": self.date,
            "ref": self.ref or self.name,
            "payment_id": self.id,
            "company_id": self.company_id.id,
        }

    def action_view_cheque_register(self):
        self.ensure_one()
        return {
            "name": _("Cheque Register"),
            "type": "ir.actions.act_window",
            "res_model": "cheque.register",
            "view_mode": "tree,form",
            "domain": [("payment_id", "=", self.id)],
            "context": {
                "default_payment_id": self.id,
                "default_direction": self.payment_type,
            },
        }

    def _reconcile_source_invoice_lines(self):
        """Reconcile payment lines with stored source invoice lines."""
        domain = [
            ("parent_state", "=", "posted"),
            ("account_type", "in", ("asset_receivable", "liability_payable")),
            ("reconciled", "=", False),
        ]
        for payment in self.filtered("to_reconcile_payment_line_ids"):
            payment_lines = payment.line_ids.filtered_domain(domain)
            source_lines = payment.to_reconcile_payment_line_ids
            for account in payment_lines.account_id:
                (payment_lines + source_lines).filtered_domain(
                    [("account_id", "=", account.id), ("reconciled", "=", False)]
                ).reconcile()
            payment.to_reconcile_payment_line_ids = False

    def action_submit(self):
        """Submit payment without triggering tier validation.

        Validation is triggered after bank export, not on submit. Assign the
        move sequence on submit so every payment gets a number immediately,
        instead of some staying unnamed ("Draft") until they are posted
        (the native name is only assigned for the first move of a period
        while it is unposted).
        """
        for payment in self:
            move = payment.move_id
            if move.state != "draft":
                raise UserError(_("Only draft payments can be submitted."))
            move.state = "submitted"
            # Payment moves do not flow through account.move.action_submit, so
            # enrol them in the approval workflow explicitly (step 1).
            move.workflow_state = "to_approve"
            move.submitted_by = self.env.user
            move.submitted_date = fields.Datetime.now()
            if move.date and (not move.name or move.name == "/"):
                move._set_next_sequence()

    @api.onchange("kmitl_payment_type_id")
    def _onchange_kmitl_payment_type_id(self):
        """The operation type sets the direction and its default voucher.

        It no longer says anything about *how* the money moves — the paying
        account does that — so it stops touching the method line.
        """
        if self.kmitl_payment_type_id:
            self.payment_type = self.kmitl_payment_type_id.direction
            if self.kmitl_payment_type_id.journal_id:
                self.journal_id = self.kmitl_payment_type_id.journal_id

    @api.onchange("payment_method_line_id")
    def _onchange_payment_method_line_id(self):
        """A paying account belongs to one voucher journal, so choosing it
        settles the voucher too.

        This inverts Odoo's direction (journal first, then its method lines) on
        purpose: here the officer knows which account the money leaves from, and
        the ใบสำคัญ follows from it — which is why the journal stays hidden on
        the form.
        """
        for payment in self:
            journal = payment.payment_method_line_id.journal_id
            if journal and payment.journal_id != journal:
                payment.journal_id = journal

    @api.depends("kmitl_payment_type_id")
    def _compute_destination_account_id(self):
        # Let base compute first (handles standard receivable/payable logic),
        # then override only when a custom account is explicitly configured.
        super()._compute_destination_account_id()
        for pay in self:
            ptype = pay.kmitl_payment_type_id
            if ptype and ptype.override_account_id:
                pay.destination_account_id = ptype.override_account_id

    def _seek_for_lines(self):
        """Treat override account as counterpart even if not receivable/payable.

        Base Odoo classifies lines as liquidity / counterpart / writeoff based on
        account type. When kmitl_payment_type uses a non-standard account
        (e.g. a deposit account that is neither receivable nor payable), base
        leaves counterpart_lines empty and puts that line in writeoff_lines.
        We re-classify it here so the rest of the payment logic works correctly.
        """
        liquidity_lines, counterpart_lines, writeoff_lines = super()._seek_for_lines()
        ptype = self.kmitl_payment_type_id
        # Only reclassify when base couldn't find a counterpart on its own.
        if ptype and ptype.override_account_id and not counterpart_lines:
            new_writeoff = self.env["account.move.line"]
            for line in writeoff_lines:
                if line.account_id == ptype.override_account_id:
                    counterpart_lines += line
                else:
                    new_writeoff += line
            writeoff_lines = new_writeoff
        return liquidity_lines, counterpart_lines, writeoff_lines

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Propagate analytic_distribution to all generated move lines.

        Base Odoo does not copy analytic_distribution from the payment to the
        move lines it creates (liquidity + counterpart). We propagate it here
        so analytic reporting reflects the correct distribution on both entries.

        Note: analytic_distribution lives on account.move (via _inherits), so
        writing it on the payment goes directly to the move — it does NOT go
        through _synchronize_to_moves and therefore must be pushed to lines here.
        """
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals)
        if self.analytic_distribution:
            for line_vals in line_vals_list:
                line_vals["analytic_distribution"] = self.analytic_distribution
        return line_vals_list

    def _get_trigger_fields_to_synchronize(self):
        # Extend the base tuple (immutable) so that changing kmitl_payment_type_id
        # also triggers a move re-synchronization (account/journal may change).
        # Deliberately NOT including payment_method_line_id: rebuilding the
        # move collapses the withholding-tax write-off lines (they are
        # recreated from name/account/amount only, losing wht_tax_id and
        # tax_base_amount). A change of paying account repoints the money line
        # surgically in write() instead.
        return (
            *super()._get_trigger_fields_to_synchronize(),
            "kmitl_payment_type_id",
        )

    def write(self, vals):
        """Follow a change of paying account (หัวจ่าย) on the journal entry.

        ``payment_method_line_id`` is deliberately kept out of the
        synchronisation triggers (a full move rebuild would collapse the
        withholding-tax write-off lines), so the money line is repointed
        surgically instead.
        """
        # The money line has to be found BEFORE the write: afterwards the
        # account it still carries is the old one, which no longer counts as a
        # liquidity account, so _seek_for_lines would no longer return it.
        stale_lines = {}
        if "payment_method_line_id" in vals:
            for payment in self:
                if payment.state in ("draft", "submitted"):
                    stale_lines[payment.id] = payment._seek_for_lines()[0]
        res = super().write(vals)
        if stale_lines:
            self._kmitl_repoint_liquidity_line(stale_lines)
        return res

    def _kmitl_repoint_liquidity_line(self, stale_lines):
        # 'submitted' counts too: a KMITL payment spends its whole exportable
        # life there, and its entry is not posted yet.
        for payment in self:
            lines = stale_lines.get(payment.id)
            if not lines:
                continue
            gl_account = payment.payment_method_line_id.payment_account_id
            if not gl_account:
                continue
            stale = lines.filtered(lambda l: l.account_id != gl_account)
            if stale:
                stale.with_context(
                    skip_account_move_synchronization=True
                ).write({"account_id": gl_account.id})

