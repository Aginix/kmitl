# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, _, api, fields, models
from odoo.addons.l10n_th_account_tax.models.withholding_tax_cert import (
    WHT_CERT_INCOME_TYPE,
)
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
    "wht_tax_id",
    "wht_amount_base",
    "partner_id",
    "payment_method_line_id",
    "currency_id",
    "payment_type",
    "partner_type",
    "journal_id",
    "date",
)

# The withholding a voucher declares itself, which is what the net amount is
# derived from. Touching either re-derives ``amount``; neither may be touched
# once the voucher is confirmed, because both move the entry.
#
# ``wht_cert_income_type`` is deliberately not one of them: it says nothing to
# the books and nothing to the bank, only to the certificate handed to the
# payee, so it stays correctable until that certificate is issued.
WHT_INPUT_FIELDS = ("wht_tax_id", "wht_amount_base")

# The payee's bank account is money side too, but it closes later than the rest,
# so it has a guard of its own. Everything above moves the books — the amount, the
# period, the account credited — and is settled the moment the voucher is
# confirmed. This one moves nothing: it is purely the instruction carried to the
# bank, and the bank is not told anything until an e-payment file leaves. Until
# then a wrong account number is a mistake nobody has acted on yet, and refusing
# the correction only forces it to be made outside the system. See ADR-0003.
PAYEE_ACCOUNT_FIELD = "partner_bank_id"


class AccountPayment(models.Model):
    _inherit = "account.payment"

    kmitl_payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Operation Type",
        required=True,
    )
    kmitl_payment_subject_id = fields.Many2one(
        comodel_name="kmitl.payment.subject",
        string="Payment Subject",
        readonly=True,
        copy=False,
        index=True,
        help="เรื่องที่จ่าย — what the disbursement this voucher belongs to was "
        "for, which is what chose its หัวจ่าย. Carried down from the request so "
        "the voucher records why the money left the account it left. Read-only "
        "because the choice was already made and acted on: changing it here "
        "would move no money and re-derive no paying account. A voucher filled "
        "in by hand has none — nothing chose its หัวจ่าย but the officer.",
    )
    payee_type_id = fields.Many2one(
        related="partner_id.partner_type_id",
        string="Payee Type",
        store=True,
        index=True,
        help="ประเภทผู้รับเงิน — what kind of counterparty the payee is, which is "
        "what carries their default payable account and withholding-tax rate. "
        "Stored so the office can filter and group its own list by it. Not to be "
        "confused with partner_type (customer / supplier), which says which side "
        "of the ledger the voucher is on and nothing about who is paid.",
    )
    to_reconcile_payment_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_payment_to_reconcile_line_rel",
        column1="payment_id",
        column2="move_line_id",
        string="Lines to Reconcile",
        copy=False,
    )
    wht_tax_id = fields.Many2one(
        comodel_name="account.withholding.tax",
        string="Withholding Tax",
        check_company=True,
        copy=False,
        help="ภาษีหัก ณ ที่จ่าย — the rate withheld on a voucher the finance "
        "office fills in by hand. Empty on a voucher raised from a disbursement: "
        "that one's withholding was decided on the bill and already sits on the "
        "entry, and a rate here as well would withhold twice. Proposed from the "
        "payee's category when a payee is picked on the form, which is the only "
        "place it is ever set — never on a voucher another document creates.",
    )
    wht_amount_base = fields.Monetary(
        string="Withholding Base",
        currency_field="currency_id",
        copy=False,
        help="ฐานเงินได้ — the income the rate is applied to, and on a voucher "
        "the finance office fills in by hand this is **the figure that is "
        "typed**: the amount paid is the base less the withholding, and follows "
        "from it. KMITL charges no VAT and a voucher withholds one thing, so the "
        "base is the whole of what the payee is owed.",
    )
    wht_cert_income_type = fields.Selection(
        selection=WHT_CERT_INCOME_TYPE,
        string="Type of Income",
        copy=False,
        help="ประเภทเงินได้ — what the payee was paid for, in the Revenue "
        "Department's own categories. It is what the certificate and the ภ.ง.ด. "
        "filing are about, and it books nothing, so it stays correctable after "
        "the money side has frozen.",
    )
    amount_wht = fields.Monetary(
        string="Withholding Tax Amount",
        compute="_compute_amount_wht",
        currency_field="currency_id",
        help="Total withholding tax withheld on this payment. Read from the "
        "voucher's own rate and base when it has them, and otherwise from the "
        "payment move lines carrying a WHT tax — which is how a voucher raised "
        "from a bill carries it. Either way it is visible in every state (the "
        "native withholding moves are only created on posting).",
    )
    amount_before_wht = fields.Monetary(
        string="Amount Before Withholding",
        compute="_compute_amount_before_wht",
        currency_field="currency_id",
        help="ยอดก่อนหัก ณ ที่จ่าย — the gross the payee is owed, read back from "
        "the amount paid and what was withheld from it. This is the figure a "
        "voucher raised from a bill is read by: nobody types it there, because "
        "the bill decided both halves. On a voucher filled in by hand the typed "
        "figure is the withholding base, which this then equals.",
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
        search="_search_needs_bank_export",
        help="Only an outbound bank transfer does. Cheques are handed over and "
        "cash is paid at the counter, so neither can ever gain an export and "
        "neither may be held back by the export gate — the finance office "
        "confirms those results by hand instead.",
    )

    cheque_ids = fields.One2many(
        comodel_name="cheque.register",
        inverse_name="payment_id",
        string="Cheques",
        help="Every cheque ever written for this voucher, including the ones "
        "that died and were replaced — each of those still holds the number it "
        "spent out of the book.",
    )
    cheque_id = fields.Many2one(
        comodel_name="cheque.register",
        string="Cheque",
        compute="_compute_cheque_id",
        search="_search_cheque_id",
        help="The one cheque that can still pay this voucher, if it has been "
        "written yet. A voucher never has two at once.",
    )
    # What the smart button shows, for the reason the disbursement link next to
    # it is a Char too: Odoo 16 has no read mode, so a Many2one in a button is
    # drawn as a text box to type in.
    cheque_number = fields.Char(
        related="cheque_id.cheque_number",
        string="Cheque Number",
    )
    finance_state_cheque = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Ready to Write the Cheque"),
            ("issued", "Cheque Issued"),
            ("paid", "Cheque Handed Over"),
        ],
        string="Finance Status",
        compute="_compute_finance_state_cheque",
        help="The same lifecycle as Finance Status, in the words that fit a "
        "cheque. A voucher settled on paper goes to no bank, so 'Confirmed for "
        "the Bank' names an errand nobody runs for it — and its Confirmed covers "
        "two different situations, one where the cheque has still to be written "
        "and one where it is written and waiting to be collected. Read-only and "
        "unstored: it says nothing finance_state and the cheque do not already "
        "say between them.",
    )

    def _wht_currency(self):
        """The currency the withholding figures are rounded in.

        Falls all the way back to the environment's company, because these run on
        a record still being filled in on screen — where the journal, and with it
        the currency, may not have been picked yet.
        """
        self.ensure_one()
        return (
            self.currency_id
            or self.company_id.currency_id
            or self.env.company.currency_id
        )

    @api.depends(
        "wht_tax_id",
        "wht_tax_id.amount",
        "wht_amount_base",
        "move_id.line_ids.wht_tax_id",
        "move_id.line_ids.balance",
    )
    def _compute_amount_wht(self):
        """What is withheld, read from whichever of the two records knows.

        A voucher the finance office filled in says so itself, on a rate and a
        base of its own — and it has to be answered from those rather than from
        the entry, because the entry is built *from* this figure and would not
        have the line yet.

        A voucher raised from a bill carries no rate here: its withholding was
        settled on the bill and reached the entry as a write-off line, so the
        entry is what knows. Reading the lines also keeps the figure visible
        while the entry is still draft, which the native withholding moves are
        not — those are only created on posting.
        """
        for payment in self:
            if payment.wht_tax_id:
                currency = payment._wht_currency()
                payment.amount_wht = currency.round(
                    payment.wht_amount_base * payment.wht_tax_id.amount / 100
                )
                continue
            wht_lines = payment.move_id.line_ids.filtered("wht_tax_id")
            payment.amount_wht = sum(abs(line.balance) for line in wht_lines)

    @api.depends("amount", "amount_wht")
    def _compute_amount_before_wht(self):
        """The gross, read back rather than stored.

        Deliberately not an input, even though on a hand-filled voucher the gross
        *is* what an officer types: there the typed figure is the withholding
        base, and a second stored copy of the same number would be one more thing
        to keep in step — and would be recomputed, from a half-updated pair,
        every time the base moved. One number, in one field, whichever end of the
        document filled it in.
        """
        for payment in self:
            payment.amount_before_wht = payment.amount + payment.amount_wht

    # -------------------------------------------------------------------------
    # Withholding tax keyed in on the voucher
    # -------------------------------------------------------------------------
    @api.onchange("partner_id", "payment_type")
    def _onchange_partner_id_wht(self):
        """Propose the payee's own rate, on the form and nowhere else.

        The payee's category is where KMITL keeps its rates
        (``res.partner.type.wht_tax_id``), and it is the same source the
        disbursement line reads — so a voucher typed by hand and a voucher billed
        through a request withhold the same on the same payee.

        This is an onchange rather than a compute on purpose. Every voucher
        raised from a disbursement request is created in Python, where onchanges
        do not run, so a rate can never appear on one of those: their withholding
        already sits on the entry, and a rate here as well would withhold twice.
        A compute would reach them and do exactly that.
        """
        for payment in self:
            if payment.payment_type != "outbound":
                payment.wht_tax_id = False
                continue
            payment.wht_tax_id = payment.partner_id.partner_type_id.wht_tax_id

    @api.onchange("wht_tax_id")
    def _onchange_wht_tax_id(self):
        """Follow the rate with the things it decides.

        The base is seeded from whatever amount has been typed so far, because
        that is what the officer meant by it: a voucher that withholds is filled
        in gross-first, and the number already in the amount box was the gross
        before anyone said a rate applied to it. Taking the rate away is the same
        move backwards, and ``_undo_withholding`` makes it.
        """
        for payment in self:
            if not payment.wht_tax_id:
                payment._undo_withholding()
                continue
            payment.wht_cert_income_type = payment.wht_tax_id.wht_cert_income_type
            if not payment.wht_amount_base:
                payment.wht_amount_base = payment.amount
            payment._apply_wht_to_amount()

    @api.onchange("wht_amount_base")
    def _onchange_wht_amount_base(self):
        """Keep the form's figures in step while they are being typed.

        The same derivation runs on save (``_apply_wht_to_amount``), which is what
        makes it true for a voucher made through the API; this is what makes the
        officer see it happen as they type, in the one screen where a voucher is
        filled in by hand.
        """
        for payment in self:
            payment._apply_wht_to_amount()

    def _apply_wht_to_amount(self):
        """Derive the amount paid from the base and the rate applied to it.

        The base is the input and the amount paid is what follows, so this runs on
        every save that touched either. On save it runs *after* the write rather
        than by rewriting the values: the amount is one of core's own
        synchronisation triggers, so writing it is what rebuilds the entry around
        the new figures, and having one derivation means the interactive form and
        an API call end up at the same numbers.

        Vouchers with no rate of their own are left alone — that is a voucher
        raised from a bill, whose amount was settled where its withholding was.
        The move backwards is ``_undo_withholding``.
        """
        for payment in self:
            if not payment.wht_tax_id:
                continue
            currency = payment._wht_currency()
            if currency.is_zero(payment.wht_amount_base):
                continue
            net = currency.round(payment.wht_amount_base - payment.amount_wht)
            if currency.compare_amounts(payment.amount, net):
                payment.amount = net
        return True

    def _undo_withholding(self):
        """Hand back what a withholding that has just been taken away withheld.

        The base standing on the voucher is what the payee was owed all along, so
        removing the rate owes them the whole of it — and the base, with nothing
        left to be a base of, goes with the type of income. Only ever reached by a
        voucher that *had* a rate, because only such a voucher has a base.
        """
        for payment in self:
            if payment.wht_tax_id or payment._wht_currency().is_zero(
                payment.wht_amount_base
            ):
                continue
            payment.amount = payment.wht_amount_base
            payment.wht_amount_base = 0.0
            payment.wht_cert_income_type = False
        return True

    def _wht_write_off_line_vals(self):
        """The withholding line of a voucher that declares its own.

        Same shape as the one a disbursement builds from its bill
        (``disbursement.payment.line._payment_amount_vals``), because it has to
        carry the same two fields: ``wht_tax_id`` and ``tax_base_amount`` are what
        the withholding moves, the certificate and the ภ.ง.ด. filing are all made
        of. Empty for a voucher without a rate of its own, which leaves the
        preserved write-off path (``_synchronize_to_moves``) to answer for the
        ones raised from a bill.
        """
        self.ensure_one()
        tax = self.wht_tax_id
        currency = self._wht_currency()
        if not tax or currency.is_zero(self.amount_wht):
            return []
        company_currency = self.company_id.currency_id or self.env.company.currency_id
        date = self.date or fields.Date.context_today(self)
        return [
            {
                "name": tax.display_name,
                "account_id": tax.account_id.id,
                "partner_id": self.partner_id.id,
                "currency_id": currency.id,
                "amount_currency": -self.amount_wht,
                "balance": currency._convert(
                    -self.amount_wht, company_currency, self.company_id, date
                ),
                "tax_base_amount": currency._convert(
                    self.wht_amount_base, company_currency, self.company_id, date
                ),
                "wht_tax_id": tax.id,
            }
        ]

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

    def _search_needs_bank_export(self, operator, value):
        """Let the flag be filtered on without restating what it means.

        It is computed and not stored, so a domain cannot reach it — and the
        alternative, spelling the rule out again in a search filter, would be the
        second place to change it and the first to drift from
        ``_compute_settlement``. This mirrors that method leaf for leaf, including
        a payment with no paying account yet (no method, so nothing says it is
        settled outside a file).
        """
        if operator not in ("=", "!="):
            raise NotImplementedError(
                "needs_bank_export can only be searched with = or !="
            )
        travels = [
            "&",
            ("payment_type", "=", "outbound"),
            "|",
            ("payment_method_line_id", "=", False),
            (
                "payment_method_line_id.payment_method_id.code",
                "not in",
                ("kmitl_cheque", "kmitl_cash"),
            ),
        ]
        if (operator == "=") == bool(value):
            return travels
        return ["!"] + travels

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

    @api.model_create_multi
    def create(self, vals_list):
        """Derive the amount paid on a voucher created with a withholding tax.

        Only ever a voucher of the finance office's own: nothing else sets a rate
        here (see ``_onchange_partner_id_wht``). The entry core has just built is
        rebuilt by the amount write, which is also what puts the withholding line
        on it.
        """
        payments = super().create(vals_list)
        with_wht = payments.filtered("wht_tax_id")
        if with_wht:
            with_wht.with_context(kmitl_wht_deriving=True)._apply_wht_to_amount()
        return payments

    def _clears_the_withholding(self, vals):
        """Whether this write is taking a voucher's withholding away."""
        return "wht_tax_id" in vals and not vals["wht_tax_id"]

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
        if not self.env.context.get("skip_account_move_synchronization"):
            money = [name for name in vals if name in MONEY_FIELDS]
            if money:
                self._check_money_side_open(
                    ", ".join(
                        description["string"]
                        for description in self.fields_get(money, ["string"]).values()
                    )
                )
            if PAYEE_ACCOUNT_FIELD in vals:
                self._check_payee_account_open()
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
        # The base and the rate are inputs; the amount paid follows from them.
        # Guarded against its own write, which lands here again with only
        # ``amount`` in it.
        if not self.env.context.get("kmitl_wht_deriving") and any(
            name in vals for name in WHT_INPUT_FIELDS
        ):
            deriving = self.with_context(kmitl_wht_deriving=True)
            if self._clears_the_withholding(vals):
                deriving._undo_withholding()
            else:
                deriving._apply_wht_to_amount()
        return res

    def _check_money_side_open(self, what):
        """Refuse to change what the bank already acted on.

        The money side is open only while the voucher is the finance office's own
        draft. From the moment it is confirmed for the bank the voucher has a
        ใบสำคัญจ่าย number, a date and an accounting period, and every field guarded
        here either is one of those or moves the entry that carries them. The
        booking side is untouched by this: the accounting maker corrects that after
        the money has left, which is what their step exists for.

        The payee's bank account is the one money-side fact this does not cover. It
        moves nothing, so it stays correctable until the instruction actually leaves
        — ``_check_payee_account_open`` below, and ADR-0003.

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
    # Into an e-payment file
    # -------------------------------------------------------------------------
    def grouped_by_paying_account(self):
        """One recordset per หัวจ่าย, in the order the payments came in.

        One file debits one account, so this is the shape every path into a file
        works in: a selection is not one batch but as many as it has paying
        accounts.
        """
        groups = {}
        for payment in self:
            paying_account = payment.payment_method_line_id
            groups[paying_account] = groups.get(paying_account, self.browse()) | payment
        return groups

    def action_create_bank_payment_export(self):
        """Put the selected vouchers into e-payment files.

        Sits on this model so the payment list can carry it as a real button
        instead of burying it in the Action menu, and delegates so that door and
        the server action behave identically.
        """
        return (
            self.env["bank.payment.export"]
            .with_context(active_ids=self.ids, active_model=self._name)
            .action_create_bank_payment_export()
        )

    def _payee_account_is_open(self):
        """Whether the payee's bank account may still be corrected.

        Open until the instruction leaves the office. For a voucher that goes out
        in an e-payment file that is the moment the file is exported — up to then
        no bank has been told anything, whatever the voucher's own status says. For
        one settled by cheque or cash the account is part of no instruction at all,
        so it closes with the rest of the voucher, when the finance office confirms
        the money reached the payee.
        """
        self.ensure_one()
        if self.needs_bank_export:
            return self.export_status != "exported"
        return self.finance_state != "paid"

    def _check_payee_account_open(self):
        for payment in self:
            if payment._payee_account_is_open():
                continue
            raise UserError(
                _(
                    "The payee's bank account cannot be changed on %(payment)s: it "
                    "has already gone to the bank in %(file)s. Reject that file if "
                    "the bank could not credit the account.",
                    payment=payment.display_name,
                    file=payment.payment_export_id.display_name
                    or _("an e-payment file"),
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
            payment._check_wht_complete()
            payment.finance_state = "confirmed"
            move = payment.move_id
            if move.date and (not move.name or move.name == "/"):
                move._set_next_sequence()
        return True

    def _check_wht_complete(self):
        """A withholding a voucher declares has to be a withholding it can state.

        Checked at the confirmation for the same reason the amount is: a monetary
        field cannot be made required (zero is a value), and a draft an officer is
        still filling in must be allowed to be incomplete. This is the moment it
        stops being one — from here the voucher is numbered, the money side is
        frozen, and the certificate handed to the payee is written from exactly
        these three figures.
        """
        self.ensure_one()
        if not self.wht_tax_id:
            return True
        currency = self._wht_currency()
        if currency.is_zero(self.wht_amount_base) or self.wht_amount_base < 0:
            raise UserError(
                _(
                    "Fill in the income the withholding on %s is calculated from "
                    "(ฐานเงินได้)."
                )
                % self.display_name
            )
        if not self.wht_cert_income_type:
            raise UserError(
                _(
                    "Choose the type of income withheld on %s: it is what the "
                    "certificate and the ภ.ง.ด. filing are about."
                )
                % self.display_name
            )
        if currency.compare_amounts(self.amount_wht, self.wht_amount_base) >= 0:
            raise UserError(
                _(
                    "The withholding on %s is not less than the amount before "
                    "withholding, so there would be nothing left to pay the payee."
                )
                % self.display_name
            )
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

    def _unmark_paid(self):
        """Withdraw the assertion that the money reached the payee.

        There is normally no way back past the Hand-over: the phase is
        forward-only because the money has left, and a confirmation given by
        mistake is corrected in the books. A cheque is the case that rule was
        never written for — the paper can die *after* the payee took it, and then
        the money never left at all. So the claim is withdrawn rather than
        corrected, and the voucher goes back to being the finance office's to
        settle with another piece of paper. See ADR-0007.

        Only while the entry is unposted, which is where a dead cheque is almost
        always caught: the voucher sits in the accounting office's queue for as
        long as their maker-checker takes. Once they have posted it the bank
        credit is in the books, and taking it out is a reversal — their work, on
        their form, and not something the finance office reaches across and does.
        """
        for payment in self:
            if payment.finance_state != "paid":
                raise UserError(
                    _("%s was not marked paid, so there is nothing to withdraw.")
                    % payment.display_name
                )
            if payment.move_id.state == "posted":
                raise UserError(
                    _(
                        "%s has already been posted, so the money has left the "
                        "books as well as the office. Ask the accounting office "
                        "to reverse the entry first."
                    )
                    % payment.display_name
                )
        self.write({"finance_state": "confirmed"})
        # Take back the Todo the Hand-over put in the accounting office's inbox.
        # A no-op for a voucher on a disbursement request: that one was never
        # raised here, because the request raises one for all of its payees.
        self.mapped("move_id").activity_unlink(
            ["finance_kmitl.mail_activity_payment_to_book"]
        )
        return True

    def action_confirm_paid(self):
        """ยืนยันจ่ายสำเร็จ — the finance office's assertion that the money reached
        the payee, for a voucher that stands on its own.

        The bank's result file never enters Odoo, so this press is the only thing
        that knows. A voucher belonging to a disbursement request is confirmed on
        the request instead, one press for all of its payees.

        A voucher paid by cheque is confirmed by **handing the cheque over**, not
        here — the same shape as a transfer, which is confirmed by closing the
        file that carried it. Cash is what is left: it is paid across the counter,
        nothing else records it, so this is where it is said.
        """
        by_cheque = self.filtered("is_cheque_payment")
        if by_cheque:
            raise UserError(
                _(
                    "These vouchers are settled by cheque, so the money reaches "
                    "the payee when the cheque does. Write the cheque and hand it "
                    "over instead: %s."
                )
                % ", ".join(by_cheque.mapped("display_name"))
            )
        self._mark_paid()
        # Through the hook, not straight to the hand-over: a voucher belonging to a
        # document that hands over for all of its own must not raise a second Todo
        # for the same work.
        self._hands_over_on_its_own()._handover_to_accounting()
        return True

    def _hands_over_on_its_own(self):
        """The vouchers whose Hand-over is theirs to make.

        A voucher raised by a document that hands over for all of its own — a
        disbursement request — is not one of them: the request puts one Todo in the
        accounting office's inbox for every payee it covers, and a second one per
        voucher would be the same work listed twice. Overridden where such a
        document exists, so that whatever marks a voucher paid does not have to know
        which documents those are.
        """
        return self

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

    @api.depends("cheque_ids.state")
    def _compute_cheque_id(self):
        for payment in self:
            payment.cheque_id = payment.cheque_ids.filtered(
                lambda cheque: cheque.state != "cancelled"
            )[:1]

    @api.depends("finance_state", "cheque_id.state")
    def _compute_finance_state_cheque(self):
        """Fold the cheque's own step into the voucher's, for the statusbar.

        The voucher has one value, ``confirmed``, for two situations a cheque
        officer keeps apart: no cheque written yet, and a cheque written and
        signed that the payee has not come for. Both are the voucher's money side
        frozen and nothing paid, so they are rightly one state — but a bar that
        cannot tell them apart is a bar that cannot show the work.
        """
        for payment in self:
            state = payment.finance_state
            if state == "confirmed" and payment.cheque_id.state == "issued":
                state = "issued"
            payment.finance_state_cheque = state

    def _search_cheque_id(self, operator, value):
        """Let the live cheque be searched, so what reads through it can be
        recomputed.

        Two computes reach a voucher's cheque this way — the number the smart
        button shows, and the date on the withholding-tax certificate — and Odoo
        works out *which* vouchers to recompute when a cheque changes by
        searching back through the field. A computed field with no search is a
        dead end there: the dependency is dropped with a warning, and the
        certificate would keep a date the cheque no longer has.

        ``False`` asks a different question from an id — "has a cheque at all"
        rather than "is this cheque" — so it flips the sense of the test rather
        than being matched against.
        """
        if operator not in ("=", "!=", "in", "not in"):
            raise NotImplementedError(
                "cheque_id can only be searched with =, !=, in or not in"
            )
        matches = operator in ("=", "in")
        domain = [("state", "!=", "cancelled")]
        asks_for_any = value is False or value is None
        if not asks_for_any:
            ids = value if isinstance(value, (list, tuple)) else [value]
            domain.append(("id", "in", ids))
        vouchers = self.env["cheque.register"].search(domain).payment_id
        if asks_for_any:
            matches = not matches
        return [("id", "in" if matches else "not in", vouchers.ids)]

    def action_post(self):
        """Validate bank export for outbound, then reconcile after posting."""
        for payment in self:
            if payment.needs_bank_export and payment.export_status == "draft":
                raise UserError(_("Payment must be exported to bank before posting."))
        res = super().action_post()
        self._reconcile_source_invoice_lines()
        return res

    # -------------------------------------------------------------------------
    # Out by cheque
    # -------------------------------------------------------------------------
    def action_create_cheques(self):
        """Start a cheque for each of the selected vouchers.

        Sits on this model and takes a whole selection for the reason
        ``action_create_bank_payment_export`` does: the office works a run of
        payments at once — a utilities run is twenty vouchers off one book — and
        the list is where all twenty are already in front of them. Opening twenty
        forms to press the same button twenty times is precisely what ADR-0006
        took out of this phase, and it should not come back on the cheque side.

        Numbers are **proposed, not assigned**: the first is the guess for the
        book and the rest run on from it in the order the vouchers came in, and
        every one is overtypable in the list this opens. A book nothing has been
        drawn on yet proposes nothing, because there is no paper to guess from.
        """
        Cheque = self.env["cheque.register"]
        self._check_cheques_can_be_written()
        vals_list = []
        running = {}
        for payment in self:
            book = payment.payment_method_line_id.bank_account_id
            if book not in running:
                running[book] = Cheque._next_number_for_book(book)
            number = running[book]
            vals_list.append(
                {
                    "payment_id": payment.id,
                    "cheque_number": number,
                    "cheque_date": fields.Date.context_today(payment),
                }
            )
            running[book] = Cheque._bump_number(number) if number else False
        cheques = Cheque.create(vals_list)
        return {
            "type": "ir.actions.act_window",
            "name": _("Cheques"),
            "res_model": "cheque.register",
            "domain": [("id", "in", cheques.ids)],
            "view_mode": "tree,form" if len(cheques) > 1 else "form",
            "res_id": cheques.id if len(cheques) == 1 else False,
            "target": "current",
        }

    def _check_cheques_can_be_written(self):
        """Refuse the selection by name rather than quietly skipping rows.

        Somebody who ticked twenty vouchers and got eighteen cheques would have to
        work out for themselves which two are missing and why, so each reason says
        which vouchers it is about.
        """
        not_cheque = self.filtered(lambda payment: not payment.is_cheque_payment)
        if not_cheque:
            raise UserError(
                _(
                    "These vouchers are not paid by cheque — their paying account "
                    "(หัวจ่าย) settles them another way: %s."
                )
                % ", ".join(not_cheque.mapped("display_name"))
            )
        unconfirmed = self.filtered(
            lambda payment: payment.finance_state != "confirmed"
        )
        if unconfirmed:
            raise UserError(
                _(
                    "A cheque may only be written for a voucher that is confirmed "
                    "for the bank, or what it is written for could still change "
                    "underneath it: %s."
                )
                % ", ".join(unconfirmed.mapped("display_name"))
            )
        written = self.filtered("cheque_id")
        if written:
            raise UserError(
                _(
                    "These vouchers already have a cheque that has not been "
                    "cancelled: %s."
                )
                % ", ".join(written.mapped("display_name"))
            )
        return True

    def action_view_cheques(self):
        """Open the cheque written for this voucher, or the whole run of paper it
        took if an earlier one died."""
        self.ensure_one()
        action = {
            "name": _("Cheques"),
            "type": "ir.actions.act_window",
            "res_model": "cheque.register",
            "domain": [("payment_id", "=", self.id)],
            "context": {"default_payment_id": self.id},
        }
        if len(self.cheque_ids) == 1:
            action.update({"view_mode": "form", "res_id": self.cheque_ids.id})
        else:
            action["view_mode"] = "tree,form"
        return action

    # -------------------------------------------------------------------------
    # The payee's withholding-tax certificate
    # -------------------------------------------------------------------------
    def action_create_wht_cert(self):
        """Issue the payee's หนังสือรับรองการหักภาษี ณ ที่จ่าย (50 ทวิ).

        The finance office issues it, because they are the ones facing the payee
        — the paper goes out with the transfer or in the payee's hand with the
        cheque, weeks before the accounting office books the voucher. Upstream
        only offers it on a *posted* entry, which for KMITL is after the
        Hand-over and far too late.

        The certificate is therefore bound to the **voucher** and not to the
        entry: ``account.move._post`` unlinks every certificate hanging off the
        entry it posts, and one already in the payee's hands must survive that.
        See ADR-0008.
        """
        self.ensure_one()
        if not self.wht_tax_id:
            raise UserError(
                _("%s withholds nothing, so there is nothing to certify.")
                % self.display_name
            )
        if self.finance_state == "draft":
            raise UserError(
                _(
                    "Confirm %s first: a certificate states what was withheld, "
                    "and until the voucher is confirmed that figure can still "
                    "change."
                )
                % self.display_name
            )
        self._check_wht_complete()
        live = self.wht_cert_ids.filtered(lambda cert: cert.state != "cancel")
        if live:
            raise UserError(
                _(
                    "%(payment)s already has a withholding-tax certificate "
                    "(%(cert)s). Cancel it before issuing another, so the payee is "
                    "never holding two."
                )
                % {"payment": self.display_name, "cert": live[:1].display_name}
            )
        cert = self.env["withholding.tax.cert"].create(self._prepare_wht_cert_vals())
        return {
            "type": "ir.actions.act_window",
            "name": _("Withholding Tax Certificate"),
            "res_model": "withholding.tax.cert",
            "view_mode": "form",
            "res_id": cert.id,
            "target": "current",
        }

    def _prepare_wht_cert_vals(self):
        """One certificate, one line — a voucher withholds one thing.

        ``move_id`` is left empty on purpose (ADR-0008), and neither ``name`` nor
        ``date`` is passed: both are computed from the payment, and the date is
        the day the money actually left rather than the voucher's own (see
        ``withholding_tax_cert.py``).
        """
        self.ensure_one()
        descriptions = dict(WHT_CERT_INCOME_TYPE)
        return {
            "payment_id": self.id,
            "partner_id": self.partner_id.id,
            "income_tax_form": self.wht_tax_id.income_tax_form,
            "tax_payer": "withholding",
            "wht_line": [
                Command.create(
                    {
                        "wht_cert_income_type": self.wht_cert_income_type,
                        "wht_cert_income_desc": descriptions.get(
                            self.wht_cert_income_type
                        ),
                        "base": self.wht_amount_base,
                        "amount": self.amount_wht,
                        "wht_tax_id": self.wht_tax_id.id,
                    }
                )
            ],
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
        # Only the vouchers whose withholding lives on the entry. One that
        # declares its own is rebuilt from its stored rate and base instead, in
        # ``_prepare_move_line_default_vals``, so there is nothing to salvage.
        for payment in self.filtered(lambda voucher: not voucher.wht_tax_id):
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
        put back (see ``_synchronize_to_moves``), and where the withholding line
        of a voucher that declares its own withholding is put *on*. The two are
        exclusive by construction: a voucher either says what it withholds
        (filled in here) or carries it from a bill (preserved from the entry),
        never both — that is what keeps a payee from being withheld twice.
        """
        own_wht = self._wht_write_off_line_vals()
        preserved = self.env.context.get("kmitl_preserved_write_off") or {}
        if own_wht:
            write_off_line_vals = own_wht
        elif preserved.get(self.id):
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
            # The voucher's own withholding: it is one line of the entry, so a
            # change to the rate or the base has to reach it. Safe to rebuild
            # from here for the reason the preserved values exist at all — this
            # line is regenerated from stored fields rather than salvaged from
            # the entry, so nothing about it can be lost in the rebuild.
            "wht_tax_id",
            "wht_amount_base",
        )
