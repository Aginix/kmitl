# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Groups that gate each post-bill payment-execution step.
AUDITOR_GROUP = "disbursement_finance_kmitl.group_disbursement_payment_auditor"
AUTHORIZER_GROUP = (
    "disbursement_finance_kmitl.group_disbursement_payment_authorizer"
)
FINANCE_GROUP = "disbursement_finance_kmitl.group_disbursement_payment_finance"

# Execution Todos fanned out to the group responsible for the next step.
TO_AUDIT_ACTIVITY = "disbursement_finance_kmitl.mail_activity_dr_to_audit"
TO_AUTHORIZE_ACTIVITY = "disbursement_finance_kmitl.mail_activity_dr_to_authorize"
TO_PAY_ACTIVITY = "disbursement_finance_kmitl.mail_activity_dr_to_pay"


class DisbursementRequest(models.Model):
    """Post-bill payment-execution workflow on the disbursement request.

    After the accounting office posts the vendor bills (``bills_posted``), the
    request enters a second, forward-only approval phase that is separate from
    the pre-bill request approval (signed/verified/approved):

        bills_posted
          -> payment_audited      (auditor       : action_audit)
          -> payment_authorized   (rector delegate: action_authorize)
          -> paid                 (finance        : action_confirm_paid)
          -> cleared              (accounting posts the payment move through the
                                   account.move maker-checker; set in
                                   account_move._post)

    Budget was already obligated/consumed once at ``approved`` and is never
    touched again here.
    """

    _inherit = "disbursement.request"

    state = fields.Selection(
        selection_add=[
            ("payment_audited", "Payment Audited"),
            ("payment_authorized", "Authorized for Disbursement"),
            ("paid", "Paid"),
            ("cleared", "Cleared"),
            ("cancel",),
        ],
        ondelete={
            "payment_audited": "set default",
            "payment_authorized": "set default",
            "paid": "set default",
            "cleared": "set default",
        },
    )

    pipeline_status = fields.Selection(
        selection_add=[
            ("payment_draft", "Payment Draft"),
            ("payment_posted", "Payment Posted"),
            ("done", "Done"),
        ],
        ondelete={
            "payment_draft": "set default",
            "payment_posted": "set default",
            "done": "set default",
        },
    )

    display_status = fields.Selection(
        selection_add=[
            ("payment_draft", "Payment Draft"),
            ("payment_posted", "Payment Posted"),
            ("done", "Done"),
            ("payment_audited", "Payment Audited"),
            ("payment_authorized", "Authorized for Disbursement"),
            ("paid", "Paid"),
            ("cleared", "Cleared"),
        ],
        ondelete={
            "payment_draft": "set default",
            "payment_posted": "set default",
            "done": "set default",
            "payment_audited": "set default",
            "payment_authorized": "set default",
            "paid": "set default",
            "cleared": "set default",
        },
    )

    # ------------------------------------------------------------------
    # Payment classification (set by the auditor during Payment Audit)
    # ------------------------------------------------------------------
    payment_subject_id = fields.Many2one(
        comodel_name="kmitl.payment.subject",
        string="Payment Subject",
        tracking=True,
        copy=False,
        help="เรื่องที่จ่าย — drives how the paying bank (หัวจ่าย) is chosen "
        "and the default payment method per line.",
    )
    payment_subject_auto_match = fields.Boolean(
        related="payment_subject_id.auto_match_payee_bank",
        string="Auto-match by Payee's Bank",
        readonly=True,
        help="Shown with the payment lines because a fallback row only reads "
        "as a problem when the subject is auto-matching in the first place.",
    )
    # One payee, one payment: the payee-level rows that each become exactly one
    # account.payment against exactly one posted bill.
    payment_line_ids = fields.One2many(
        comodel_name="disbursement.payment.line",
        inverse_name="request_id",
        string="Payment Lines",
        copy=False,
    )
    payment_amount_net = fields.Monetary(
        string="Total Net to Pay",
        compute="_compute_payment_amount_net",
        currency_field="currency_id",
        help="What will actually leave the bank for the payments about to be "
        "created.",
    )

    @api.depends(
        "payment_line_ids.amount_net",
        "payment_line_ids.payment_id",
        "payment_line_ids.bill_id.state",
        "payment_line_ids.bill_id.payment_state",
    )
    def _compute_payment_amount_net(self):
        for record in self:
            record.payment_amount_net = sum(
                record._payable_payment_lines().mapped("amount_net")
            )

    @api.onchange("payment_subject_id")
    def _onchange_payment_subject_id(self):
        """Re-derive the payment lines the auditor did not pick by hand.

        The match result records who chose each paying account, so a hand-picked
        one (``manual``) is preserved while everything derived from the previous
        subject follows the new one.
        """
        if self.payment_subject_id:
            lines = self.payment_line_ids.filtered(lambda l: not l.payment_id)
            derived = lines.filtered(
                lambda l: l.paying_account_match != "manual"
            )
            derived.update(
                {"paying_account_id": False, "paying_account_match": False}
            )
            self._apply_subject_defaults(lines)

    def _apply_subject_defaults(self, lines):
        """Fill the paying account (หัวจ่าย) on ``lines`` from the subject,
        leaving values a person already set alone.

        A subject that auto-matches serves each payee from the allowed account
        held at their own bank — that is what pays a staff advance out of the
        payee's bank without any extra setting — and stamps how each line was
        resolved so the auditor can review the ones that fell to the fallback.
        """
        self.ensure_one()
        subject = self.payment_subject_id
        if not subject:
            return
        for line in lines.filtered(lambda l: not l.payment_id):
            if not line.paying_account_id:
                account, match = subject._paying_account_with_match(
                    line.partner_bank_id.bank_id, company=self.company_id
                )
                line.paying_account_id = account
                line.paying_account_match = match if account else False

    # ------------------------------------------------------------------
    # Payment lines (one payee, one payment)
    # ------------------------------------------------------------------
    def _ensure_payment_lines(self):
        """Make a payment line for every posted bill that has none, then bring
        the amounts of the rows no payment has frozen up to date.

        Idempotent and cheap to call, so it runs at every door into the payment
        phase rather than only at the ``bills_posted`` transition: a request can
        then never show an empty payment tab, a bill accounting reversed and
        re-issued picks up its own row unaided, and a database whose requests
        predate this model needs no migration.

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
                PaymentLine.create([
                    record._prepare_payment_line_vals(bill) for bill in missing
                ])
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

    def _payable_payment_lines(self):
        """The payment lines a payment is still to be created for.

        A row whose bill was reversed or already paid stays on the request as a
        record of what was reviewed, but is not paid again.
        """
        self.ensure_one()
        return self.payment_line_ids.filtered(
            lambda line: not line.payment_id
            and line.bill_id.state == "posted"
            and line.bill_id.payment_state == "not_paid"
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
    payment_move_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_payment_info",
        string="Payment Journal Entries",
    )
    payment_move_count = fields.Integer(
        compute="_compute_payment_info",
        string="Payment Move Count",
    )

    @api.depends("payment_ids", "payment_ids.state", "payment_ids.move_id")
    def _compute_payment_info(self):
        for rec in self:
            active = rec.payment_ids.filtered(lambda p: p.state != "cancel")
            total = len(active)
            rec.payment_count = total
            posted = len(active.filtered(lambda p: p.state == "posted"))
            rec.payment_status_display = (
                _("จ่ายแล้ว %s/%s", posted, total) if total else ""
            )
            moves = active.mapped("move_id")
            rec.payment_move_ids = moves
            rec.payment_move_count = len(moves)

    @api.depends(
        "state",
        "bill_ids",
        "bill_ids.state",
        "bill_ids.payment_state",
        "payment_ids",
        "payment_ids.state",
    )
    def _compute_pipeline_status(self):
        # Base sets pre_approval/approved; the accounting bridge sets
        # bill_draft/bill_posted while state is approved/bills_posted.
        super()._compute_pipeline_status()
        for rec in self:
            if rec.state == "cleared":
                rec.pipeline_status = "done"
            elif rec.state in ("payment_authorized", "paid"):
                active = rec.payment_ids.filtered(lambda p: p.state != "cancel")
                if active.filtered(lambda p: p.state == "posted"):
                    rec.pipeline_status = "payment_posted"
                elif active:
                    rec.pipeline_status = "payment_draft"

    # ------------------------------------------------------------------
    # Todo fan-out (mirrors accounting_kmitl_workflow._schedule_approval_todo)
    # ------------------------------------------------------------------
    def _schedule_payment_todo(self, activity_xmlid, group_xmlid):
        """Push an execution Todo to every member of the responsible group."""
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group:
            return
        for rec in self:
            for user in group.users:
                rec.activity_schedule(
                    activity_xmlid, user_id=user.id, note=rec.name or ""
                )

    def write(self, vals):
        res = super().write(vals)
        # Entering bills_posted (set by the accounting bridge when the last
        # bill posts) opens the payment-execution phase: lay out the payee-level
        # payment lines and notify the auditors.
        if vals.get("state") == "bills_posted":
            self._ensure_payment_lines()
            self._schedule_payment_todo(TO_AUDIT_ACTIVITY, AUDITOR_GROUP)
        return res

    # ------------------------------------------------------------------
    # Payment classification helpers
    # ------------------------------------------------------------------
    def _check_payment_classification(self):
        """Validate the classification before confirming the audit.

        Fills the empty method / paying account from the subject, then blocks
        with an actionable error listing the offending payees when the
        classification cannot drive payment creation.

        The checks that once forced every item of a payee into agreement are
        gone: one payee is one payment line, so mixed methods, mixed paying
        accounts and mixed recipient banks are no longer states the data can
        reach. Nor can a method disagree with its account — the account names
        the method.
        """
        for record in self:
            subject = record.payment_subject_id
            if not subject:
                raise UserError(
                    _("Select the payment subject (เรื่องที่จ่าย) before "
                      "confirming the audit.")
                )
            record._ensure_payment_lines()
            lines = record._payable_payment_lines()

            no_account = lines.filtered(lambda l: not l.paying_account_id)
            if no_account:
                raise UserError(
                    _(
                        "Payees with no paying account (หัวจ่าย) — set the "
                        "allowed accounts on subject '%(subject)s' or pick one "
                        "per line: %(payees)s",
                        subject=subject.name,
                        payees=", ".join(
                            sorted(set(no_account.mapped("partner_id.name")))
                        ),
                    )
                )
            if subject.allowed_paying_account_ids:
                not_allowed = lines.filtered(
                    lambda l: l.paying_account_id
                    not in subject.allowed_paying_account_ids
                )
                if not_allowed:
                    raise UserError(
                        _(
                            "Paying accounts not allowed for subject "
                            "'%(subject)s': %(accounts)s",
                            subject=subject.name,
                            accounts=", ".join(
                                sorted(set(
                                    not_allowed.mapped(
                                        "paying_account_id.display_name"
                                    )
                                ))
                            ),
                        )
                    )

            # A cheque is handed over and cash is counted out; only a payment
            # that travels through the banking system needs the payee's account.
            transfer_lines = lines.filtered(
                lambda l: not l.paying_account_id.is_cheque
                and not l.paying_account_id.is_cash
            )
            no_bank = transfer_lines.filtered(lambda l: not l.partner_bank_id)
            if no_bank:
                raise UserError(
                    _(
                        "Transfer payees without a bank account (switch them "
                        "to cheque or add the account): %s"
                    )
                    % ", ".join(no_bank.mapped("partner_id.name"))
                )
        return True

    # ------------------------------------------------------------------
    # Workflow actions (forward-only, no reject in this phase)
    # ------------------------------------------------------------------
    def action_audit(self):
        """Auditor verifies the disbursement after the bills are posted.

        Confirming the audit locks in the payment classification: subject,
        per-line method, and a resolvable paying journal for every payee.
        """
        for record in self:
            if record.state != "bills_posted":
                raise UserError(
                    _("Only bills-posted requests can be audited.")
                )
            record._check_payment_classification()
            record.state = "payment_audited"
            record.activity_feedback([TO_AUDIT_ACTIVITY])
            record._schedule_payment_todo(TO_AUTHORIZE_ACTIVITY, AUTHORIZER_GROUP)
        return True

    def action_authorize(self):
        """Rector delegate authorizes the disbursement (approve to pay)."""
        for record in self:
            if record.state != "payment_audited":
                raise UserError(
                    _("Only audited requests can be authorized for payment.")
                )
            record.state = "payment_authorized"
            record.activity_feedback([TO_AUTHORIZE_ACTIVITY])
            record._schedule_payment_todo(TO_PAY_ACTIVITY, FINANCE_GROUP)
        return True

    def action_confirm_paid(self):
        """Finance confirms the bank actually paid every payment of the DR."""
        for record in self:
            if record.state != "payment_authorized":
                raise UserError(
                    _("Only authorized requests can be confirmed as paid.")
                )
            active = record.payment_ids.filtered(lambda p: p.state != "cancel")
            if not active:
                raise UserError(
                    _("Create the payment(s) before confirming the payment.")
                )
            not_success = active.filtered(
                lambda p: p.bank_result_status != "success"
            )
            if not_success:
                raise UserError(
                    _(
                        "The bank has not confirmed success for payment(s): "
                        "%s. Mark the bank result on the payment export first."
                    )
                    % ", ".join(not_success.mapped("name"))
                )
            record.state = "paid"
            record.activity_feedback([TO_PAY_ACTIVITY])
        return True

    def _payment_batch(self, single_method, valid_state):
        """Run a per-record action in isolated savepoints (mirror of
        accounting_kmitl_workflow.action_approve_batch)."""
        candidates = self.filtered(lambda r: r.state == valid_state)
        done = self.browse()
        failures = []
        for record in candidates:
            try:
                with self.env.cr.savepoint():
                    getattr(record, single_method)()
                done |= record
            except (UserError, ValidationError) as error:
                self.env.invalidate_all()
                failures.append(
                    (record.display_name, error.args and error.args[0] or _("error"))
                )
            except Exception as error:  # noqa: BLE001 - isolate per-record
                self.env.invalidate_all()
                failures.append((record.display_name, str(error)))
        message = _("%s request(s) processed.") % len(done)
        if failures:
            message += "\n" + _("Could not process:") + "\n"
            message += "\n".join(
                "• %s — %s" % (name, reason) for name, reason in failures
            )
        if failures and not done:
            notification_type = "danger"
        elif failures:
            notification_type = "warning"
        else:
            notification_type = "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Disbursement"),
                "message": message,
                "type": notification_type,
                "sticky": bool(failures),
            },
        }

    def action_audit_batch(self):
        return self._payment_batch("action_audit", "bills_posted")

    def action_authorize_batch(self):
        return self._payment_batch("action_authorize", "payment_audited")

    # ------------------------------------------------------------------
    # Cancel guard
    # ------------------------------------------------------------------
    def action_cancel(self):
        """Block cancel once paid/cleared or when a payment is posted."""
        for record in self:
            if record.state == "cancel":
                continue
            if record.state in ("paid", "cleared"):
                raise UserError(
                    _("Cannot cancel a request that is already paid/cleared.")
                )
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
    # Payment review and creation (finance)
    # ------------------------------------------------------------------
    def _check_payment_ready(self):
        """Refuse to review or create payments the request cannot support.

        Runs before the review opens so the officer meets the problem on the
        button rather than after reading through twenty rows.
        """
        self.ensure_one()
        if self.state != "payment_authorized":
            raise UserError(
                _("The disbursement must be authorized before creating "
                  "the payment.")
            )
        existing_payments = self.payment_ids.filtered(
            lambda p: p.state != "cancel"
        )
        if existing_payments:
            raise UserError(
                _(
                    "Cannot create new payment: existing payment(s) %s are "
                    "still in progress. Cancel them first before creating a "
                    "new one."
                )
                % ", ".join(existing_payments.mapped("name"))
            )
        self._ensure_payment_lines()
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
        lines = self._payable_payment_lines()
        if not lines:
            raise UserError(_("No posted unpaid bills to pay."))
        return lines

    def action_open_payment_wizard(self):
        """Open the Payment Review — the finance office's read-back of every
        payment line before the payments are created.

        A checkpoint, not an approval: nothing changes state here. Only the
        banking coordinates may be corrected, and closing the dialog leaves the
        request exactly as it was.
        """
        self.ensure_one()
        self._check_payment_ready()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payment Review"),
            "res_model": "disbursement.request",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(
                self.env.ref(
                    "disbursement_finance_kmitl."
                    "view_disbursement_request_payment_review"
                ).id,
                "form",
            )],
            "target": "new",
        }

    def action_create_payment(self):
        """Create draft payments from the DR, one per payment line.

        Submitting them is deliberately left to the officer: submitting is what
        makes a payment exportable to the bank and what registers a cheque, so
        it is a decision about timing rather than a consequence of creation.
        """
        self.ensure_one()
        lines = self._check_payment_ready()

        # The paying account (หัวจ่าย) carries both the account the money leaves
        # and the operation type it leaves by; the journal is the voucher type
        # (ใบสำคัญ) configured on that operation type, not a bank account.
        self._check_payment_classification()

        payments = self.env["account.payment"]
        for line in lines:
            bill = line.bill_id
            payment_type = line.paying_account_id.payment_type_id
            journal = payment_type.journal_id if payment_type else False
            if not journal:
                journal = self.env["account.journal"].search(
                    [
                        ("type", "=", "bank"),
                        ("company_id", "=", self.company_id.id),
                    ],
                    order="sequence, id",
                    limit=1,
                )
            if not journal:
                raise UserError(
                    _(
                        "No voucher journal (ใบสำคัญ) configured on the "
                        "outbound payment type, and no bank journal found for "
                        "company %s."
                    )
                    % self.company_id.name
                )
            payable_lines = bill.line_ids.filtered(
                lambda l: l.account_type == "liability_payable"
                and not l.reconciled
            )
            # One helper works out the money for both the row the officer just
            # reviewed and the payment about to carry it, so the two cannot
            # state different amounts.
            amount_bill, amount_wht, write_off_line_vals = (
                line._payment_amount_vals()
            )

            payment_vals = {
                "disbursement_request_id": self.id,
                "partner_id": bill.partner_id.id,
                "amount": amount_bill - amount_wht,
                "currency_id": bill.currency_id.id,
                "journal_id": journal.id,
                # The recipient bank is the one reviewed on the payment line:
                # left to Odoo's compute it would silently fall back to the
                # payee's first account, which is not what anyone chose.
                "partner_bank_id": line.partner_bank_id.id or False,
                "paying_account_id": line.paying_account_id.id,
                "payment_type": "outbound",
                "partner_type": "supplier",
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
            # Stamping the payment freezes the row: from here the payment is
            # the record of what left the bank.
            line.write({
                "amount_bill": amount_bill,
                "amount_wht": amount_wht,
                "amount_net": amount_bill - amount_wht,
                "payment_id": payment.id,
            })
            payments |= payment

        for payment in payments:
            pay_link = (
                "/web#id=%d&model=account.payment&view_type=form" % payment.id
            )
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

        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "domain": [("id", "in", payments.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

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

    def action_view_payment_moves(self):
        """Open journal entries linked to payments."""
        self.ensure_one()
        moves = self.payment_move_ids
        if len(moves) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Journal Entry"),
                "res_model": "account.move",
                "res_id": moves.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการล้างหนี้"),
            "res_model": "account.move",
            "domain": [("id", "in", moves.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }
