# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# The facts the bank acted on. Frozen the moment the voucher is confirmed for the
# bank: changing any of them afterwards makes the record disagree with what the
# bank was told to do, and the accounting entry would then book something that
# never happened.
#
# ``date`` is one of them. There is a single date field and it is both the day the
# money left and the accounting period, so freezing it is what keeps the
# withholding-tax certificate and the ภ.ง.ด. filing in the month the payment was
# actually made — an entry is always booked in the period the money left.
#
# What is *not* here is the booking side: the analytic distribution, the reference,
# the attachments and the operation type (and through it the counterpart account).
# That side is the accounting maker's to correct, which is the whole reason their
# office has a maker step. See ``disbursement_finance_kmitl`` ADR-0005.
MONEY_FIELDS = (
    "amount",
    "partner_id",
    "partner_bank_id",
    "payment_method_line_id",
    "currency_id",
    "payment_type",
    "partner_type",
    "journal_id",
    "date",
)


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

    finance_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed for the Bank"),
            ("paid", "Paid"),
        ],
        string="Finance Status",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
        index=True,
        help="สถานะฝั่งการเงิน — where the voucher stands in the finance office's "
        "hands, kept apart from the accounting office's own status: a payment "
        "voucher stays draft for the accounting office throughout, and only they "
        "move it. Confirmed for the Bank freezes the money side, gives the voucher "
        "its number and is what an e-payment file may carry; Paid is the finance "
        "office's assertion that the money reached the payee, and hands the voucher "
        "to the accounting office to book.",
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
        help="ผลการจ่าย — the outcome as the finance office noted it for this "
        "voucher. Nothing gates on it: the bank's own result file is never "
        "imported into Odoo, so what the system acts on is the finance office's "
        "assertion in Finance Status, and this is one more note beside it.",
    )
    is_cheque_payment = fields.Boolean(
        compute="_compute_settlement",
        help="Read from the paying account's own method, so it cannot disagree "
        "with how the money actually leaves.",
    )
    needs_bank_export = fields.Boolean(
        string="Travels in an E-Payment File",
        compute="_compute_settlement",
        help="Only an outbound bank transfer does. Cheques are handed over and "
        "cash is paid at the counter, so neither can ever gain an export and "
        "neither may be held back by the export gate — the finance office "
        "confirms those results by hand instead.",
    )

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

    @api.depends("payment_type", "payment_method_line_id.payment_method_id.code")
    def _compute_settlement(self):
        """How the money actually leaves, read off the paying account.

        The paying account is what the officer picked, so it cannot disagree
        with itself the way a second flag elsewhere could.
        """
        for payment in self:
            code = payment.payment_method_line_id.payment_method_id.code
            payment.is_cheque_payment = code == "kmitl_cheque"
            payment.needs_bank_export = (
                payment.payment_type == "outbound"
                and code not in ("kmitl_cheque", "kmitl_cash")
            )

    @api.model
    def _get_method_codes_using_bank_account(self):
        """KMITL settles by its own methods, so core never shows the bank account.

        Core looks for the ``manual`` method to decide whether the recipient
        bank account is worth displaying; every KMITL payment carries one of its
        own codes instead, so the account number stayed hidden even though a
        transfer cannot leave without one.
        """
        return super()._get_method_codes_using_bank_account() + ["kmitl_transfer"]

    @api.model
    def _get_method_codes_needing_bank_account(self):
        """Only a transfer needs an account number.

        A cheque is handed over and cash is paid at the counter, so neither can
        be held back for the want of a bank account.
        """
        return super()._get_method_codes_needing_bank_account() + ["kmitl_transfer"]

    def write(self, vals):
        """Guard the money side, and repoint the money line when the paying
        account changes.

        ``payment_method_line_id`` is deliberately not a synchronisation trigger
        (rebuilding the move recreates the withholding-tax write-off lines from
        name/account/amount and loses ``wht_tax_id``), so a change of paying
        account would otherwise leave the entry crediting the previous account.
        The money line is captured **before** the write: afterwards it still
        carries the old account and therefore no longer counts as a liquidity
        line, so looking it up then finds nothing and the correction silently
        does nothing.
        """
        money = [name for name in vals if name in MONEY_FIELDS]
        if money and not self.env.context.get("skip_account_move_synchronization"):
            self._check_money_side_open(
                ", ".join(
                    description["string"]
                    for description in self.fields_get(money, ["string"]).values()
                )
            )
        liquidity_lines = {}
        if "payment_method_line_id" in vals:
            liquidity_lines = {
                payment.id: payment._seek_for_lines()[0]
                for payment in self
                if payment.move_id.state not in ("posted", "cancel")
            }
        res = super().write(vals)
        for payment in self:
            lines = liquidity_lines.get(payment.id)
            if lines and payment.outstanding_account_id:
                lines.write({"account_id": payment.outstanding_account_id.id})
        return res

    def _check_money_side_open(self, what):
        """Refuse to change what the bank already acted on.

        The money side is open only while the voucher is the finance office's own
        draft. From the moment it is confirmed for the bank it is either in a file,
        at the bank, or booked — and in all three the record has to keep saying what
        was actually instructed. The booking side is untouched by this: the
        accounting maker corrects that after the money has left, which is what
        their step exists for.

        ``what`` is the label of whatever is being changed, built by the caller
        from its own model, so the message names the field the person just edited
        rather than the guard's own vocabulary.
        """
        for payment in self:
            if payment.finance_state == "draft":
                continue
            raise UserError(
                _(
                    "%(what)s cannot be changed on %(payment)s: the voucher is "
                    "already confirmed for the bank, so this is what the bank was "
                    "told to do. Only the booking (dimensions, operation type, "
                    "description) may still be corrected.",
                    what=what,
                    payment=payment.display_name,
                )
            )
        return True

    # -------------------------------------------------------------------------
    # The finance office's own lifecycle (ADR-0005)
    # -------------------------------------------------------------------------
    def action_confirm_for_bank(self):
        """ยืนยันพร้อมส่งธนาคาร — the finance office's first press.

        Freezes the money side and gives the voucher its ใบสำคัญจ่าย number, which
        together are what an e-payment file needs: a file may only carry vouchers
        that can no longer change underneath it, and a row referring to an
        unnumbered payment reads as "Draft Payment" in the file.

        It asks the accounting office nothing — their own status is untouched and
        the voucher stays their draft until the Hand-over.

        The amount is guarded here rather than on save: a monetary field cannot be
        made required (zero is a value), and an officer filling a payment in must be
        free to keep the draft before the figure is known. This is the moment it
        stops being a draft — from here it can go in a file and reach a bank.
        """
        for payment in self:
            if payment.finance_state != "draft":
                raise UserError(
                    _("%s is already confirmed for the bank.") % payment.display_name
                )
            if not payment.payment_method_line_id:
                raise UserError(
                    _("Choose the paying account (หัวจ่าย) of %s first.")
                    % payment.display_name
                )
            if payment.currency_id.is_zero(payment.amount) or payment.amount < 0:
                raise UserError(_("The amount must be greater than zero."))
            payment.finance_state = "confirmed"
            move = payment.move_id
            if move.date and (not move.name or move.name == "/"):
                move._set_next_sequence()
        return True

    def action_unconfirm(self):
        """Take a voucher back off the bank's desk while nothing has been sent.

        The money side is frozen because the bank was told what to do; until the
        voucher is actually in a file there is nothing to protect, so a correction
        is a correction rather than a contradiction. Once it is in a file the way
        back is closed — and after the Hand-over there is none at all: the phase is
        forward-only, and a confirmation given by mistake is corrected in the books.
        """
        for payment in self:
            if payment.finance_state != "confirmed":
                raise UserError(
                    _("Only a voucher confirmed for the bank can be unconfirmed.")
                )
            if payment.export_status != "draft":
                raise UserError(
                    _(
                        "%s is already in an e-payment file. Cancel or reject that "
                        "file first if it has not been sent."
                    )
                    % payment.display_name
                )
            payment.finance_state = "draft"
        return True

    def _mark_paid(self):
        """Move the vouchers to paid — the Hand-over itself.

        Shared by a payment confirming itself and by a disbursement request
        confirming all of its at once, so the two cannot mean different things.
        """
        for payment in self:
            if payment.finance_state != "confirmed":
                raise UserError(
                    _(
                        "%s has not been confirmed for the bank, so there is "
                        "nothing to report the outcome of yet."
                    )
                    % payment.display_name
                )
        self.write({"finance_state": "paid"})
        return True

    def action_confirm_paid(self):
        """ยืนยันจ่ายสำเร็จ — the finance office's assertion that the money reached
        the payee, for a voucher that stands on its own.

        The bank's result file never enters Odoo, so this press is the only thing
        that knows. A voucher belonging to a disbursement request is confirmed on
        the request instead, one press for all of its payees.
        """
        self._mark_paid()
        self._handover_to_accounting()
        return True

    def _handover_to_accounting(self):
        """Put the voucher in the accounting office's inbox.

        Only for a voucher that stands on its own. Work on a disbursement request
        reaches them through the request, which is the document KMITL navigates by
        — one Todo for the request rather than one per payee.
        """
        activity = self.env.ref(
            "finance_kmitl.mail_activity_payment_to_book", raise_if_not_found=False
        )
        makers = self.env.ref(
            "accounting_kmitl.group_accounting_kmitl_user", raise_if_not_found=False
        )
        if not activity or not makers:
            return False
        for payment in self:
            for maker in makers.users:
                payment.move_id.activity_schedule(
                    "finance_kmitl.mail_activity_payment_to_book",
                    user_id=maker.id,
                    note=payment.display_name,
                )
        return True

    def action_mark_bank_result_success(self):
        """Finance confirms by hand that a cheque or cash payment was paid.

        Transfers are confirmed from the bank payment export line, which also
        logs the e-payment result; nothing reports back for the payments that
        never enter a file.
        """
        self.write({"bank_result_status": "success"})

    def action_mark_bank_result_failed(self):
        self.write({"bank_result_status": "failed"})

    @api.depends("cheque_register_ids")
    def _compute_cheque_register_count(self):
        for payment in self:
            payment.cheque_register_count = len(payment.cheque_register_ids)

    def action_post(self):
        """Validate bank export for outbound, then reconcile after posting."""
        for payment in self:
            if payment.needs_bank_export and payment.export_status == "draft":
                raise UserError(_("Payment must be exported to bank before posting."))
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
            self.env["cheque.register"].create(payment._prepare_cheque_register_vals())

    def _prepare_cheque_register_vals(self):
        self.ensure_one()
        return {
            "direction": self.payment_type,
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "journal_id": self.journal_id.id,
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

    @api.onchange("kmitl_payment_type_id")
    def _onchange_kmitl_payment_type_id(self):
        """The operation type only proposes its voucher.

        How the money leaves is the paying account's business
        (``payment_method_line_id``), so nothing here touches it — a payment
        made from a disbursement carries the paying account its payee was
        reviewed with, and one made by hand keeps whatever the officer picked.
        """
        if self.kmitl_payment_type_id:
            self.payment_type = self.kmitl_payment_type_id.direction
            if self.kmitl_payment_type_id.journal_id:
                self.journal_id = self.kmitl_payment_type_id.journal_id

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

    def _write_off_line_vals(self, line):
        """The full create values of a write-off line.

        Core's rebuild keeps the amount and throws away everything the line
        *means*; this keeps the withholding-tax identity with it.
        """
        return {
            "name": line.name,
            "account_id": line.account_id.id,
            "partner_id": line.partner_id.id,
            "currency_id": line.currency_id.id,
            "amount_currency": line.amount_currency,
            "balance": line.balance,
            "wht_tax_id": line.wht_tax_id.id,
            "tax_base_amount": line.tax_base_amount,
        }

    def _synchronize_to_moves(self, changed_fields):
        """Rebuild the entry without losing the withholding tax.

        Core preserves only the *amount* of the write-off lines: it merges them
        into a single dict of name/account/partner/currency taken from the first
        one, deletes the real lines and re-creates from that. Two WHT deductions
        therefore come back as one anonymous line, and ``wht_tax_id`` /
        ``tax_base_amount`` — the fields the WHT certificate and the ภ.ง.ด. report
        are made of — are gone.

        This matters now that the accounting maker corrects the operation type
        *after* the money has left (ADR-0005): the rebuild that used to be
        theoretical is a normal step. Rather than reimplement core's rebuild, the
        richer per-line values are stashed for ``_prepare_move_line_default_vals``
        to use in place of the poorer ones core computes — same flow, one
        substitution, and the counterpart amount is unchanged because the sums are
        equal either way.
        """
        if self.env.context.get("skip_account_move_synchronization") or not any(
            name in changed_fields for name in self._get_trigger_fields_to_synchronize()
        ):
            return super()._synchronize_to_moves(changed_fields)
        preserved = {}
        for payment in self:
            write_off_lines = payment._seek_for_lines()[2].filtered("wht_tax_id")
            if write_off_lines:
                preserved[payment.id] = [
                    payment._write_off_line_vals(line) for line in write_off_lines
                ]
        if not preserved:
            return super()._synchronize_to_moves(changed_fields)
        records = self.with_context(kmitl_preserved_write_off=preserved)
        return super(AccountPayment, records)._synchronize_to_moves(changed_fields)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Propagate analytic_distribution to all generated move lines.

        Base Odoo does not copy analytic_distribution from the payment to the
        move lines it creates (liquidity + counterpart). We propagate it here
        so analytic reporting reflects the correct distribution on both entries.

        Note: analytic_distribution lives on account.move (via _inherits), so
        writing it on the payment goes directly to the move — it does NOT go
        through _synchronize_to_moves and therefore must be pushed to lines here.

        This is also where the write-off values a rebuild would have flattened are
        put back (see ``_synchronize_to_moves``).
        """
        preserved = self.env.context.get("kmitl_preserved_write_off") or {}
        if preserved.get(self.id):
            write_off_line_vals = preserved[self.id]
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
        # tax_base_amount). The method line is instead set in the create values
        # so the move is built against the right outstanding account from the
        # start, and a UI change of the operation type re-synchronises through
        # kmitl_payment_type_id anyway.
        return (
            *super()._get_trigger_fields_to_synchronize(),
            "kmitl_payment_type_id",
        )
