# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# What the paper itself says, and therefore what may not change once the paper
# exists. The number is printed on it; the date is printed on it *and* is the day
# the law says the payee was paid, which the withholding-tax certificate is dated
# from. Everything else about a cheque — who is paid, how much, out of which
# account — is the voucher's and is already frozen there.
PAPER_FIELDS = ("cheque_number", "cheque_date")

# Why a cheque will never pay anyone. Declared here and reused by the wizard that
# asks for it, so the two cannot come to offer different answers.
CANCEL_REASONS = [
    ("bounced", "Bounced"),
    ("lost", "Lost"),
    ("stale", "Uncashed and Out of Date"),
    ("misdrawn", "Drawn Incorrectly"),
    ("misprinted", "Spoiled in Printing"),
]


class ChequeRegister(models.Model):
    """เช็คจ่าย — one cheque, written for one payment voucher.

    What an **ไฟล์ e-Payment** is to a bank transfer, this is to a cheque: the
    thing that stands between the voucher being confirmed for the bank and the
    voucher being paid, and that carries what the finance office does in between.
    The difference is arity. A file is one instruction covering many payees, so it
    is a document of its own with its own payees, amounts and dates. A cheque
    covers exactly one payee, so it states none of those: they are the voucher's,
    read through ``payment_id``, and there is no second copy to drift.

    What is genuinely the cheque's own is the paper — its number, the cheque book
    it was torn from, the date written on it, and whether it was printed, handed
    over, or died. See ADR-0006.

    **A number is spent, not held.** Nothing here reserves or allocates numbers:
    the cheque book is pre-printed and the paper is what decides. ``cheque_number``
    is typed in, and ``next_cheque_number`` is a *guess* — the highest number
    already used in the same book, plus one. A guess that is wrong is overtyped,
    and nothing downstream is any the worse. This is deliberately not an
    ``ir.sequence``: a stored counter that drifts from the paper would state a
    wrong number confidently, and the bank, not Odoo, decides which cheque is
    which.
    """

    _name = "cheque.register"
    _description = "Cheque"
    _inherit = ["mail.thread", "mail.activity.mixin", "thai.date.mixin"]
    _order = "cheque_date desc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    # ``cascade`` because a cheque states nothing of its own: with the voucher
    # gone there is no payee, no amount and no cheque book left to read, so the
    # row could only survive as a number attached to nothing. The number it spent
    # goes with it, which the guess simply absorbs — that is what makes a guess a
    # guess.
    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment Voucher",
        required=True,
        index=True,
        copy=False,
        ondelete="cascade",
        tracking=True,
        help="ใบสำคัญจ่าย this cheque was written for. One cheque pays one "
        "voucher, and the voucher is what carries the payee, the amount and the "
        "paying account — so the cheque restates none of them.",
    )

    # ------------------------------------------------------------------
    # Read from the voucher, never copied. The voucher's money side is frozen
    # from the moment it is confirmed for the bank, and a cheque cannot exist
    # before that, so these are settled facts by the time they are stored.
    # ------------------------------------------------------------------
    partner_id = fields.Many2one(
        related="payment_id.partner_id",
        string="Payee",
        store=True,
        index=True,
    )
    amount = fields.Monetary(
        related="payment_id.amount",
        string="Amount",
        store=True,
        currency_field="currency_id",
        help="What the cheque is written for — the net amount the voucher pays, "
        "after withholding tax.",
    )
    currency_id = fields.Many2one(
        related="payment_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="payment_id.company_id",
        store=True,
        index=True,
    )
    paying_account_id = fields.Many2one(
        related="payment_id.payment_method_line_id",
        string="Paying Account",
        store=True,
        help="หัวจ่าย the voucher is paid from, which is what names the cheque "
        "book below.",
    )
    cheque_book_id = fields.Many2one(
        related="payment_id.payment_method_line_id.bank_account_id",
        string="Cheque Book",
        store=True,
        index=True,
        help="เล่มเช็ค — the institute's own bank account this cheque is drawn "
        "on, which is what a cheque book is. It is the paying account's bank "
        "account, never the journal: a journal is a voucher type (ใบสำคัญ) and "
        "holds no bank account at all. Numbers run without repeating within one "
        "book and say nothing across books.",
    )
    bank_id = fields.Many2one(
        related="cheque_book_id.bank_id",
        string="Bank",
        store=True,
        help="Which bank's printed form this is, and therefore which print "
        "calibration is used.",
    )

    # ------------------------------------------------------------------
    # The paper
    # ------------------------------------------------------------------
    cheque_number = fields.Char(
        string="Cheque No.",
        copy=False,
        tracking=True,
        index=True,
        help="The number pre-printed on the paper, read off it rather than "
        "issued here.",
    )
    next_cheque_number = fields.Char(
        string="Next in the Book",
        compute="_compute_next_cheque_number",
        help="A guess at what the number should be — one past the highest "
        "already used in this cheque book. Nothing is reserved and nothing is "
        "counted: overtype it whenever the paper says otherwise.",
    )
    cheque_date = fields.Date(
        string="Cheque Date",
        required=True,
        default=fields.Date.context_today,
        copy=False,
        tracking=True,
        help="วันที่บนเช็ค — the day the payee may present it, which is the day "
        "the law treats the income as paid. The withholding-tax certificate is "
        "dated from it, so it is the cheque's counterpart to an e-payment file's "
        "effective date. Not the day the cheque was handed over, which has no "
        "tax effect at all.",
    )
    handover_date = fields.Date(
        string="Handover Date",
        copy=False,
        tracking=True,
        help="The day the payee actually took the cheque. Internal control "
        "only — it dates nothing in the books and nothing in a tax filing.",
    )
    crossed = fields.Boolean(
        string="A/C Payee Only",
        default=True,
        help="Print the 'A/C PAYEE ONLY' crossing when printing the cheque.",
    )
    strike_bearer = fields.Boolean(
        string="Strike 'or Bearer'",
        default=True,
        help="Strike out the pre-printed 'หรือผู้ถือ' (or bearer) wording when "
        "printing the cheque.",
    )
    note = fields.Text(string="Notes")

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("paid", "Handed Over"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
        index=True,
    )
    cancel_reason = fields.Selection(
        selection=CANCEL_REASONS,
        string="Cancellation Reason",
        copy=False,
        tracking=True,
        help="Why this cheque will never pay anyone. It is a note beside the "
        "cancellation, not a status of its own: to the register every death is "
        "the same fact — the number was spent and nobody was paid.",
    )

    _sql_constraints = [
        (
            "cheque_number_book_uniq",
            "unique(cheque_book_id, cheque_number)",
            "A cheque number can only be used once in a cheque book. A "
            "cancelled cheque still holds the number it was torn off with — a "
            "spent number is never handed to a second payee.",
        ),
    ]

    # ------------------------------------------------------------------
    # Numbering — a guess, held nowhere
    # ------------------------------------------------------------------
    @api.model
    def _last_number_in_book(self, cheque_book):
        """The highest number already spent in this cheque book, or False.

        Compared as numbers rather than as text, because cheque numbers carry
        leading zeros and ``"0512010" < "0512009"`` is true of strings and false
        of cheques. Cancelled cheques count: their paper is gone but their number
        is spent, so the next one is past them too.
        """
        if not cheque_book:
            return False
        spent = self.search(
            [
                ("cheque_book_id", "=", cheque_book.id),
                ("cheque_number", "!=", False),
            ]
        ).mapped("cheque_number")
        numeric = [number for number in spent if number.isdigit()]
        if not numeric:
            return False
        # Longer wins a tie so the padding of the fuller form is what carries on.
        return max(numeric, key=lambda number: (int(number), len(number)))

    @api.model
    def _bump_number(self, number):
        """One past ``number``, keeping the width the book prints in.

        ``zfill`` and not a format string: the width comes from the paper we have
        seen, so a book numbering ``0512007`` keeps its leading zero and one
        numbering ``512007`` never gains one.
        """
        return str(int(number) + 1).zfill(len(number))

    @api.model
    def _next_number_for_book(self, cheque_book):
        """The guess: one past the last spent in the book, or nothing to guess
        from."""
        last = self._last_number_in_book(cheque_book)
        return self._bump_number(last) if last else False

    @api.depends("cheque_book_id")
    def _compute_next_cheque_number(self):
        for cheque in self:
            cheque.next_cheque_number = self._next_number_for_book(
                cheque.cheque_book_id
            )

    @api.onchange("payment_id")
    def _onchange_payment_id(self):
        """Offer the guess on a cheque somebody is filling in by hand.

        ``action_create_cheques`` numbers the run it makes, but a cheque started
        from this form got nothing, so the officer retyped a number the system
        could have proposed. A book nothing has been drawn on yet still proposes
        nothing — there is no paper to guess from, and that first number is what
        the run-numbering wizard is for.
        """
        for cheque in self:
            if cheque.cheque_number:
                continue
            cheque.cheque_number = self._next_number_for_book(cheque.cheque_book_id)

    def action_open_assign_numbers(self):
        """Number a whole run from one starting number.

        The guess chains off the last number spent, so it has nothing to say
        about the first cheque out of a fresh book — and therefore nothing to say
        about any of them, the first time. This is where the officer says where
        the run starts, once.
        """
        self._check_numberable()
        return {
            "type": "ir.actions.act_window",
            "name": _("Number the Cheques"),
            "res_model": "cheque.register.assign.numbers",
            "view_mode": "form",
            "target": "new",
            "context": {"default_cheque_ids": [(6, 0, self.ids)]},
        }

    def _check_numberable(self):
        """A run is numbered while it is still paper nobody has written on."""
        issued = self.filtered(lambda cheque: cheque.state != "draft")
        if issued:
            raise UserError(
                _(
                    "These cheques have already been issued, so their numbers are "
                    "printed on paper and cannot be reassigned: %s."
                )
                % ", ".join(issued.mapped("display_name"))
            )
        books = self.mapped("cheque_book_id")
        if len(books) > 1:
            raise UserError(
                _(
                    "Numbers run within one cheque book. This selection spans "
                    "%s, so number them one book at a time."
                )
                % ", ".join(books.mapped("display_name"))
            )
        return True

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "cheque.register"
                ) or _("New")
        return super().create(vals_list)

    def name_get(self):
        """Show the number the bank knows the cheque by, once there is one.

        Nobody looks a cheque up by its register reference — they have the paper,
        or a bank statement line, and both say the number.
        """
        return [
            (cheque.id, cheque.cheque_number or cheque.name) for cheque in self
        ]

    def write(self, vals):
        """Refuse to change what the paper already says.

        Once a cheque is issued its number and its date are printed on a physical
        form that has left this system's control; editing them here would make the
        register disagree with the only copy that matters. Everything else — the
        note, the handover date, the status — is still the office's to record.
        """
        paper = [name for name in vals if name in PAPER_FIELDS]
        if paper:
            self._check_paper_open(
                ", ".join(
                    description["string"]
                    for description in self.fields_get(paper, ["string"]).values()
                )
            )
        return super().write(vals)

    def _check_paper_open(self, what):
        for cheque in self:
            if cheque.state == "draft":
                continue
            raise UserError(
                _(
                    "%(what)s cannot be changed on %(cheque)s: the cheque has "
                    "already been issued, so this is what is printed on the "
                    "paper. Cancel it and write a new one if the paper is wrong.",
                    what=what,
                    cheque=cheque.display_name,
                )
            )
        return True

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("state", "cheque_number")
    def _check_cheque_number_required(self):
        """A draft may sit without a number — the officer has the voucher before
        they have the paper. From the moment the cheque is issued the number is
        what it is."""
        for cheque in self:
            if cheque.state != "draft" and not cheque.cheque_number:
                raise ValidationError(
                    _("A cheque number is required before the cheque is issued.")
                )

    @api.constrains("payment_id", "state")
    def _check_one_live_cheque_per_voucher(self):
        """One voucher, one cheque — but only one *live* one.

        A cheque that died and was replaced leaves its row behind, holding the
        number it spent, so a voucher accumulates as many rows as it took pieces
        of paper. What may never happen is two of them able to pay the same payee
        at once.
        """
        for cheque in self:
            if cheque.state == "cancelled":
                continue
            if self.search_count(
                [
                    ("id", "!=", cheque.id),
                    ("payment_id", "=", cheque.payment_id.id),
                    ("state", "!=", "cancelled"),
                ]
            ):
                raise ValidationError(
                    _(
                        "%s already has a cheque that has not been cancelled. "
                        "Cancel it before writing another one, or the same payee "
                        "could be paid twice."
                    )
                    % cheque.payment_id.display_name
                )

    @api.constrains("payment_id")
    def _check_payment_is_a_confirmed_cheque(self):
        """A cheque may only be written for a voucher that is paid by cheque and
        can no longer change underneath it — the same gate an e-payment file puts
        on the vouchers it may carry."""
        for cheque in self:
            payment = cheque.payment_id
            if not payment.is_cheque_payment:
                raise ValidationError(
                    _(
                        "%s is not paid by cheque. Its paying account (หัวจ่าย) "
                        "settles it another way."
                    )
                    % payment.display_name
                )
            if payment.finance_state == "draft":
                raise ValidationError(
                    _(
                        "%s has not been confirmed for the bank yet, so what the "
                        "cheque would be written for can still change."
                    )
                    % payment.display_name
                )
            if not cheque.cheque_book_id:
                raise ValidationError(
                    _(
                        "%s names no bank account, so there is no cheque book to "
                        "draw on. Set it in Finance ▸ Settings ▸ Paying Accounts."
                    )
                    % payment.payment_method_line_id.display_name
                )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def action_issue(self):
        """ออกเช็ค — the paper now exists, with its number and its date on it.

        It says nothing about who has it. A cheque printed and signed can wait in
        the drawer for days until the payee sends someone to collect it, which is
        why this is not the last state: the claim that the money reached them is
        มอบเช็ค, one press later. The same distinction an e-payment file draws
        between ออกไฟล์แล้ว and จ่ายสำเร็จ, and for the same reason (ADR-0004).
        """
        for cheque in self:
            if cheque.state != "draft":
                raise UserError(
                    _("%s has already been issued.") % cheque.display_name
                )
            if not cheque.cheque_number:
                raise UserError(
                    _("Enter the number printed on %s before issuing it.")
                    % cheque.display_name
                )
        self.write({"state": "issued"})
        return True

    def action_hand_over(self):
        """มอบเช็ค — the payee has the cheque, so the money has reached them.

        This is the **Hand-over**: it marks the voucher paid and puts it in the
        accounting office's inbox, which is exactly what closing an e-payment file
        does for the payees that file carried. The order below is that method's,
        kept identical so one settlement cannot come to mean something the other
        does not.
        """
        for cheque in self:
            if cheque.state != "issued":
                raise UserError(
                    _(
                        "%s has not been issued yet, so there is nobody it could "
                        "have been handed to."
                    )
                    % cheque.display_name
                )
        for cheque in self:
            if not cheque.handover_date:
                cheque.handover_date = fields.Date.context_today(cheque)
        # Only the vouchers still waiting, exactly as closing an e-payment file
        # does: ``_mark_paid`` refuses anything that is not ``confirmed``, so a
        # voucher some other press already carried across would make this one fail
        # rather than record the hand-over it was pressed for.
        vouchers = self.payment_id.filtered(
            lambda payment: payment.finance_state == "confirmed"
        )
        vouchers._mark_paid()
        # Through the hook: a voucher on a document that hands over for all of its
        # own must not raise a second Todo for the same work.
        vouchers._hands_over_on_its_own()._handover_to_accounting()
        self.write({"state": "paid"})
        return True

    def action_open_cancel(self):
        """Ask why, because the reason is only known at this moment."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cancel Cheque"),
            "res_model": "cheque.register.cancel",
            "view_mode": "form",
            "target": "new",
            "context": {"default_cheque_id": self.id},
        }

    def _cancel(self, reason, replace=False):
        """ยกเลิกเช็ค — the paper is dead and this number will never pay anyone.

        Whatever killed it — bounced, lost, uncashed until it went out of date,
        drawn wrong, spoiled in the printer — the register keeps one fact: the
        number was spent and nobody was paid. The reason sits beside it as a note,
        because a status per cause would be five names for one thing.

        A cheque that had already been handed over takes its voucher back with it.
        มอบเช็ค was the assertion that the money reached the payee, and it did
        not, so the assertion is withdrawn: the voucher returns to confirmed and
        can no longer be posted. What does *not* move is the obligation — the same
        bill, payee, amount and dimensions — so the replacement is another cheque
        on the same voucher rather than a new voucher, which would claim a new
        obligation had arisen. See ADR-0007.
        """
        replacements = self.browse()
        for cheque in self:
            if cheque.state == "cancelled":
                raise UserError(
                    _("%s is already cancelled.") % cheque.display_name
                )
        self.filtered(lambda cheque: cheque.state == "paid").mapped(
            "payment_id"
        )._unmark_paid()
        self.write({"state": "cancelled", "cancel_reason": reason})
        if replace:
            # One at a time so each replacement's guess sees the one before it;
            # preparing them all up front would guess the same number twice.
            for cheque in self:
                replacements |= self.create(cheque._prepare_replacement_vals())
        return replacements

    def _prepare_replacement_vals(self):
        """The next cheque for the same voucher.

        Dated today rather than the dead cheque's date: it is a different piece of
        paper and the payee may present it from the day it is written, which is
        also the day the withholding is dated from. Crossing and the struck bearer
        line follow the cheque being replaced — those were how this payee is paid,
        not facts about the paper that died.
        """
        self.ensure_one()
        return {
            "payment_id": self.payment_id.id,
            "cheque_number": self._next_number_for_book(self.cheque_book_id),
            "cheque_date": fields.Date.context_today(self),
            "crossed": self.crossed,
            "strike_bearer": self.strike_bearer,
        }

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    def amount_in_words(self):
        """Amount spelled out in Thai baht text (for the cheque)."""
        self.ensure_one()
        return self.currency_id.with_context(lang="th_TH").amount_to_text(self.amount)

    def date_digits(self, buddhist_year=False):
        """Return the cheque date as ``DDMMYYYY`` digits for the date boxes."""
        self.ensure_one()
        if not self.cheque_date:
            return ""
        date = self.cheque_date
        year = date.year + 543 if buddhist_year else date.year
        return "%02d%02d%04d" % (date.day, date.month, year)

    def action_print_cheque(self):
        """Print the cheque onto the bank's own form.

        Only once it has been issued: the number and the date are settled by that
        press, and printing before it would put on paper something the register
        still considers open to change.
        """
        for cheque in self:
            if cheque.state == "draft":
                raise UserError(
                    _(
                        "Issue %s first. Printing settles the number and the date "
                        "onto paper, so they are settled here beforehand."
                    )
                    % cheque.display_name
                )
            if cheque.state == "cancelled":
                raise UserError(
                    _("%s was cancelled and must not be printed again.")
                    % cheque.display_name
                )
        return self.env.ref("finance_kmitl.action_report_cheque_print").report_action(
            self
        )
