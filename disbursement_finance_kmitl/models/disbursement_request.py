# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DisbursementRequest(models.Model):
    """The request's side of the payment phase: what is paid, to whom, from where.

    Data only. *When* it happens — audit, authorise, pay, clear — is a work
    station each (``disbursement_wst_payment_audit``, ``_payment_authorize``,
    ``_pay``, ``_clear``): this bridge owns the payment lines, the vouchers and
    their links, and names no station (disbursement_wst ADR-0004).
    """

    _inherit = "disbursement.request"

    payment_subject_id = fields.Many2one(
        comodel_name="kmitl.payment.subject",
        string="Payment Subject",
        copy=False,
        tracking=True,
        help="What this disbursement is for, which is what decides the paying "
        "account (หัวจ่าย) each payee is served from. Chosen once by the "
        "auditor; individual payees can still be moved onto another account.",
    )
    payment_auto_match = fields.Boolean(
        related="payment_subject_id.auto_match_payee_bank",
        string="Auto-match by Payee's Bank",
        readonly=True,
    )
    payment_line_ids = fields.One2many(
        comodel_name="disbursement.payment.line",
        inverse_name="request_id",
        string="Payment Lines",
        copy=False,
    )

    # One2many via the stored back-reference on account.payment, so payment
    # progress recomputes reactively (no search() inside computes).
    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="disbursement_request_id",
        string="Payments",
        copy=False,
    )
    payment_count = fields.Integer(
        compute="_compute_payment_info",
        string="Payment Count",
    )
    payment_status_display = fields.Char(
        string="Payment Status",
        compute="_compute_payment_info",
    )

    @api.depends(
        "payment_ids",
        "payment_ids.state",
        "payment_ids.finance_state",
    )
    def _compute_payment_info(self):
        """Payment progress as the finance office means it.

        "จ่ายแล้ว" counts the vouchers whose money has left — ``finance_state ==
        'paid'`` — and not the ones the accounting office has posted. Those are
        two different offices' facts about the same document (ADR-0005): a
        request can be paid in full with nothing booked yet, and reading `state`
        here reported it as nothing paid.

        ``state`` still decides which vouchers are counted at all, because
        cancelling is not one office's opinion — a cancelled voucher is no
        longer a payment of this request in anybody's ledger.
        """
        for rec in self:
            active = rec.payment_ids.filtered(lambda p: p.state != "cancel")
            total = len(active)
            rec.payment_count = total
            paid = len(active.filtered(lambda p: p.finance_state == "paid"))
            rec.payment_status_display = _("จ่ายแล้ว %s/%s", paid, total) if total else ""

    def write(self, vals):
        res = super().write(vals)
        # A new subject re-derives every row it is allowed to.
        if "payment_subject_id" in vals:
            for record in self:
                record._apply_subject_defaults(record.payment_line_ids)
        return res

    @api.depends("payment_ids.state", "payment_ids.finance_state")
    def _compute_is_settled(self):
        """Settled once every live voucher has its money — the finance office's
        fact, not the accounting office's: the entry may not be booked yet."""
        for rec in self:
            active = rec.payment_ids.filtered(lambda p: p.state != "cancel")
            rec.is_settled = bool(active) and all(
                p.finance_state == "paid" for p in active
            )

    # ------------------------------------------------------------------
    # Payment lines (one per payee)
    # ------------------------------------------------------------------
    def _ensure_payment_lines(self):
        """Make a payment line for every posted bill that has none, then bring
        the amounts of the rows no payment has frozen up to date.

        Idempotent and cheap to call, so it runs at every door into the payment
        phase rather than only when the audit station is entered: a request can
        then never show an empty payment tab, and a bill accounting reversed and
        re-issued picks up its own row unaided.

        Runs sudo because it is a system derivation — the accounting user who
        posts the last bill triggers it without holding rights on these rows.

        See ``docs/adr/0003-ensure-payment-lines-on-access.md``.
        """
        PaymentLine = self.env["disbursement.payment.line"].sudo()
        for record in self.sudo():
            billed = record.payment_line_ids.mapped("bill_id")
            missing = record.bill_ids.filtered(
                lambda bill: bill.state == "posted" and bill not in billed
            )
            if missing:
                PaymentLine.create(
                    [record._prepare_payment_line_vals(bill) for bill in missing]
                )
            record._apply_subject_defaults(record.payment_line_ids)
            record.payment_line_ids._refresh_amounts()
        # Read back through the caller's own environment: the rows were made
        # sudo, and everything downstream reads them as the acting user.
        self.invalidate_recordset(["payment_line_ids"])
        return True

    def _prepare_payment_line_vals(self, bill):
        """Prepare a payment line for ``bill``.

        The payee's bank starts from the bill, which is the recipient the
        accounting document already states.
        """
        self.ensure_one()
        return {
            "request_id": self.id,
            "bill_id": bill.id,
            "partner_bank_id": bill.partner_bank_id.id or False,
        }

    @api.onchange("payment_subject_id")
    def _onchange_payment_subject_id(self):
        """Fill in every payee's หัวจ่าย the moment the subject is picked.

        The same derivation ``write`` runs, one step earlier. The auditor's job
        in this step is to check which account each payee is served from, and
        that can only be done while the form is still open: leaving the accounts
        (and the fallback rows that want re-checking) to appear after the save
        turns one pass over the payees into two.
        """
        self._apply_subject_defaults(self.payment_line_ids)

    def _apply_subject_defaults(self, lines):
        """Derive the paying account of every row the subject still owns.

        Rows a person picked by hand (``manual``) and rows a payment already
        owns are left alone — both already carry a decision that re-deriving
        would quietly overwrite.

        Written sudo because the rows only *follow* the subject: whoever may
        choose it may have them follow, exactly as ``_ensure_payment_lines``
        may make them in the first place. What a row may still be changed at
        all is a rule about the workflow rather than about who is asking, so
        the editability guard on the row is untouched by this.
        """
        self.ensure_one()
        subject = self.payment_subject_id
        for line in lines.sudo():
            if line.payment_id or line.paying_account_match == "manual":
                continue
            if not subject:
                continue
            account, match = subject._paying_account_with_match(
                line.partner_bank_id.bank_id
            )
            line.write(
                {
                    "paying_account_id": account.id if account else False,
                    "paying_account_match": match if account else False,
                }
            )
        return True

    def _payable_payment_lines(self):
        """The payment lines a payment is still to be created for.

        A row whose bill was reversed or already paid stays on the request as a
        record of what was reviewed, but is not paid again.
        """
        self.ensure_one()
        return self.payment_line_ids.filtered(
            lambda line: (
                not line.payment_id
                and line.bill_id.state == "posted"
                and line.bill_id.payment_state == "not_paid"
            )
        )

    def _check_payment_classification(self):
        """Refuse to move on while a payee has no usable banking coordinates.

        Phrased against the payees rather than against the configuration, so the
        error names the rows to fix rather than a field the reader may not even
        be able to see.
        """
        self.ensure_one()
        if not self.payment_subject_id:
            raise UserError(
                _(
                    "Choose the payment subject before auditing: it is what decides "
                    "which account each payee is paid from."
                )
            )
        lines = self._payable_payment_lines()
        if not lines:
            raise UserError(_("There is no posted unpaid bill to pay on this request."))
        no_account = lines.filtered(lambda line: not line.paying_account_id)
        if no_account:
            raise UserError(
                _("No paying account for: %s.")
                % ", ".join(no_account.mapped("partner_id.display_name"))
            )
        transfers = lines.filtered(
            lambda line: line.payment_method_id.code == "kmitl_transfer"
        )
        no_bank = transfers.filtered(lambda line: not line.partner_bank_id)
        if no_bank:
            raise UserError(
                _(
                    "These payees are paid by transfer but have no bank "
                    "account: %s. Add one, or move them onto a cheque or cash "
                    "paying account."
                )
                % ", ".join(no_bank.mapped("partner_id.display_name"))
            )
        blind = lines.filtered(
            lambda line: (
                line.payment_method_id.code == "kmitl_transfer"
                and not line.paying_account_id.bank_account_id
            )
        )
        if blind:
            raise UserError(
                _(
                    "%s names no bank account, so the e-payment file would "
                    "carry no sending account. Set it in "
                    "Finance ▸ Settings ▸ Paying Accounts."
                )
                % ", ".join(set(blind.mapped("paying_account_id.display_name")))
            )
        # A cheque needs the same bank account for a different reason: it is the
        # cheque book the paper is torn from, and it is what keeps cheque numbers
        # from repeating. Checked here because this is the only checkpoint on the
        # banking coordinates — after it the vouchers are raised and the finance
        # office has nothing to fix it with but the voucher itself.
        bookless = lines.filtered(
            lambda line: (
                line.payment_method_id.code == "kmitl_cheque"
                and not line.paying_account_id.bank_account_id
            )
        )
        if bookless:
            raise UserError(
                _(
                    "%s names no bank account, so there is no cheque book to "
                    "draw on. Set it in Finance ▸ Settings ▸ Paying Accounts."
                )
                % ", ".join(set(bookless.mapped("paying_account_id.display_name")))
            )
        return True

    # ------------------------------------------------------------------
    # Cancel guard
    # ------------------------------------------------------------------
    def action_cancel(self):
        """Block cancel once a payment is posted or in progress."""
        for record in self:
            if record.state == "cancel":
                continue
            active = record.payment_ids.filtered(lambda p: p.state != "cancel")
            posted = active.filtered(lambda p: p.state == "posted")
            if posted:
                raise UserError(
                    _(
                        "Cannot cancel: payment(s) %s already posted. "
                        "Reverse them first."
                    )
                    % ", ".join(posted.mapped("name"))
                )
            if active:
                raise UserError(
                    _(
                        "Cannot cancel: there are payment(s) in progress. "
                        "Remove them first."
                    )
                )
        return super().action_cancel()

    # ------------------------------------------------------------------
    # Payment creation
    # ------------------------------------------------------------------
    def _create_payments(self):
        """Raise one numbered voucher per payee, confirmed for the bank.

        Confirming is part of raising them rather than a later errand: a file may
        only carry vouchers that can no longer change underneath it, so the gate
        the e-payment export reads and the moment the voucher is made are the same
        moment. It is also what gives each one its ใบสำคัญจ่าย number, which is
        why the chatter can name them.
        """
        self.ensure_one()
        existing_payments = self.payment_ids.filtered(lambda p: p.state != "cancel")
        if existing_payments:
            raise UserError(
                _(
                    "Cannot create new payment: existing payment(s) %s are "
                    "still in progress. Cancel them first before creating a "
                    "new one."
                )
                % ", ".join(existing_payments.mapped("name"))
            )
        partial_bills = self.bill_ids.filtered(
            lambda b: b.state == "posted" and b.payment_state == "partial"
        )
        if partial_bills:
            raise UserError(
                _(
                    "Partial payment is not supported. Bill(s) %s are already "
                    "partially paid."
                )
                % ", ".join(partial_bills.mapped("name"))
            )
        self._ensure_payment_lines()
        self._check_payment_classification()
        lines = self._payable_payment_lines()

        payment_type = self.env.ref(
            "finance_kmitl.payment_type_normal_outbound",
            raise_if_not_found=False,
        )

        payments = self.env["account.payment"]
        for line in lines:
            bill = line.bill_id
            payable_lines = bill.line_ids.filtered(
                lambda ml: ml.account_type == "liability_payable" and not ml.reconciled
            )
            amount, amount_wht, write_off_line_vals = line._payment_amount_vals()

            payment_vals = {
                "disbursement_request_id": self.id,
                "partner_id": bill.partner_id.id,
                "partner_bank_id": line.partner_bank_id.id or False,
                "amount": amount - amount_wht,
                "currency_id": bill.currency_id.id,
                # The paying account settles the voucher, not the other way
                # round: it belongs to exactly one journal, so taking the
                # journal from it is what keeps the two from disagreeing.
                "journal_id": line.paying_account_id.journal_id.id,
                "payment_method_line_id": line.paying_account_id.id,
                "payment_type": "outbound",
                "partner_type": "supplier",
                # Why this voucher leaves the account it leaves: the subject is
                # what chose the payee's หัวจ่าย, so it travels with it.
                "kmitl_payment_subject_id": self.payment_subject_id.id,
                "ref": _("%s - %s", self.name, bill.name),
                "analytic_distribution": bill.analytic_distribution,
            }
            if write_off_line_vals:
                payment_vals["write_off_line_vals"] = write_off_line_vals
            if payment_type:
                payment_vals["kmitl_payment_type_id"] = payment_type.id

            payment = self.env["account.payment"].create(payment_vals)
            payment.to_reconcile_payment_line_ids = payable_lines
            if bill.analytic_distribution:
                payment.move_id.line_ids.write(
                    {"analytic_distribution": bill.analytic_distribution}
                )
            line.payment_id = payment
            payments |= payment

        # Ahead of the chatter, because this is the press that numbers them: a
        # note naming "Payment (* 42)" would help nobody look the voucher up.
        payments.action_confirm_for_bank()

        for payment in payments:
            pay_link = "/web#id=%d&model=account.payment&view_type=form" % payment.id
            self.message_post(
                body=_(
                    'Payment <a href="%(link)s" target="_blank">'
                    "%(name)s</a> created for %(partner)s.",
                    link=pay_link,
                    name=payment.name,
                    partner=payment.partner_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

        return payments

    def action_view_payments(self):
        """Open related payment(s) in list view."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "domain": [("id", "in", self.payment_ids.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }
