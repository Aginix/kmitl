# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Groups that gate each post-bill payment-execution step.
AUDITOR_GROUP = "disbursement_finance_kmitl.group_disbursement_payment_auditor"
AUTHORIZER_GROUP = "disbursement_finance_kmitl.group_disbursement_payment_authorizer"
FINANCE_GROUP = "disbursement_finance_kmitl.group_disbursement_payment_finance"
# The accounting office's makers, who book the vouchers once the request is paid.
ACCOUNTING_MAKER_GROUP = "accounting_kmitl.group_accounting_kmitl_user"

# Execution Todos fanned out to the group responsible for the next step.
TO_AUDIT_ACTIVITY = "disbursement_finance_kmitl.mail_activity_dr_to_audit"
TO_AUTHORIZE_ACTIVITY = "disbursement_finance_kmitl.mail_activity_dr_to_authorize"
TO_PAY_ACTIVITY = "disbursement_finance_kmitl.mail_activity_dr_to_pay"
TO_BOOK_ACTIVITY = "disbursement_finance_kmitl.mail_activity_dr_to_book"


class DisbursementRequest(models.Model):
    """Post-bill payment-execution workflow on the disbursement request.

    After the accounting office posts the vendor bills (``bills_posted``), the
    request enters a second, forward-only approval phase that is separate from
    the pre-bill request approval (signed/verified/approved):

        bills_posted
          -> payment_audited      (auditor       : action_audit)
          -> payment_authorized   (rector delegate: action_authorize, which also
                                   raises the vouchers, numbered and confirmed
                                   for the bank -- see ADR-0006)
          -> paid                 (no press: reached when the last of the request's
                                   vouchers is paid, which happens as each officer
                                   closes the e-payment file they handled -- see
                                   ADR-0007)
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

    # Who performed each round-2 step, and when. Round 1 stamps its two approvals
    # the same way (``finance_approver_id`` / ``rector_approver_id``); round 2 used
    # to leave the answer in the chatter alone, which is not something a list can
    # be built on. The authorizer's history list stands on the stamp rather than on
    # the state, so a request stays in it once it is paid and cleared.
    payment_auditor_id = fields.Many2one(
        comodel_name="res.users",
        string="Payment Auditor",
        copy=False,
        readonly=True,
    )
    payment_audit_date = fields.Datetime(
        string="Payment Audited On",
        copy=False,
        readonly=True,
    )
    payment_authorizer_id = fields.Many2one(
        comodel_name="res.users",
        string="Payment Authorizer",
        copy=False,
        readonly=True,
    )
    payment_authorize_date = fields.Datetime(
        string="Payment Authorized On",
        copy=False,
        readonly=True,
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

    @api.depends(
        "payment_ids",
        "payment_ids.state",
        "payment_ids.finance_state",
        "payment_ids.move_id",
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
        # bill posts) opens the payment-execution phase: notify the auditors.
        if vals.get("state") == "bills_posted":
            self._ensure_payment_lines()
            self._schedule_payment_todo(TO_AUDIT_ACTIVITY, AUDITOR_GROUP)
        # A new subject re-derives every row it is allowed to.
        if "payment_subject_id" in vals:
            for record in self:
                record._apply_subject_defaults(record.payment_line_ids)
        return res

    # ------------------------------------------------------------------
    # Payment lines (one per payee)
    # ------------------------------------------------------------------
    def _ensure_payment_lines(self):
        """Make a payment line for every posted bill that has none, then bring
        the amounts of the rows no payment has frozen up to date.

        Idempotent and cheap to call, so it runs at every door into the payment
        phase rather than only at the ``bills_posted`` transition: a request can
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
        return True

    # ------------------------------------------------------------------
    # Workflow actions (forward-only, no reject in this phase)
    # ------------------------------------------------------------------
    def action_audit(self):
        """Auditor verifies the disbursement after the bills are posted."""
        for record in self:
            if record.state != "bills_posted":
                raise UserError(_("Only bills-posted requests can be audited."))
            record._ensure_payment_lines()
            record._check_payment_classification()
            record.write(
                {
                    "state": "payment_audited",
                    "payment_auditor_id": self.env.user.id,
                    "payment_audit_date": fields.Datetime.now(),
                }
            )
            record.activity_feedback([TO_AUDIT_ACTIVITY])
            record._schedule_payment_todo(TO_AUTHORIZE_ACTIVITY, AUTHORIZER_GROUP)
        return True

    def action_authorize(self):
        """Rector delegate authorizes the disbursement, which raises its vouchers.

        The authorisation is what makes the money payable, so it is also what
        issues the ใบสำคัญจ่าย: the finance office finds them numbered and
        confirmed for the bank, ready to go straight into an e-payment file,
        instead of a request they must first turn into payments one press per
        payee. See ADR-0006.
        """
        for record in self:
            if record.state != "payment_audited":
                raise UserError(
                    _("Only audited requests can be authorized for payment.")
                )
            record.write(
                {
                    "state": "payment_authorized",
                    "payment_authorizer_id": self.env.user.id,
                    "payment_authorize_date": fields.Datetime.now(),
                }
            )
            record.activity_feedback([TO_AUTHORIZE_ACTIVITY])
            record._schedule_payment_todo(TO_PAY_ACTIVITY, FINANCE_GROUP)
            record._try_create_payments()
        return True

    def _try_create_payments(self):
        """Raise the vouchers without letting a failure undo the authorisation.

        What can go wrong here is a banking coordinate — a payee with no account,
        a หัวจ่าย naming no bank — and none of it is the authorizer's to fix or to
        be stopped by. So the request is authorized either way: the reason goes in
        the chatter, the finance office's Todo stays where it is, and Create
        Payment is the way back in once the coordinate is corrected.

        The savepoint is what keeps a failed batch from taking the state write
        with it (same pattern as ``_payment_batch``); the message is posted
        outside it, or it would be rolled back too.

        Runs sudo because raising the vouchers is a system derivation: the
        authorizer holds no accounting rights, exactly as the accounting user who
        posts the last bill holds none on the payment lines ``_ensure_payment_lines``
        makes for them (ADR-0003). The finance office's own press keeps its own
        identity — a voucher they create is created by them.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self.sudo()._create_payments()
        except (UserError, ValidationError) as error:
            self.env.invalidate_all()
            self.message_post(
                body=_(
                    "The payment vouchers could not be raised: %s Correct it, "
                    "then use Create Payment.",
                    error.args and error.args[0] or _("error"),
                ),
                subtype_xmlid="mail.mt_note",
            )
        return True

    def action_confirm_paid(self):
        """The finance office's one confirmation that every payee has their money.

        It **writes** the outcome it asserts onto every payment rather than
        demanding that someone set it elsewhere first: the bank's own result file
        never enters Odoo, so no other record can know it, and asking the officer
        to tick each payee before ticking the request is a second pass over the
        same judgement. What is checked instead is a fact the system does hold —
        that the payments which travel in an e-payment file were actually put in
        one. Whatever the bank rejected was chased and settled outside the system
        before this is pressed.

        This is also the **Hand-over**: it is where the request stops being the
        finance office's and its vouchers enter the accounting office's approval
        queue. See ADR-0004.
        """
        for record in self:
            if record.state != "payment_authorized":
                raise UserError(_("Only authorized requests can be confirmed as paid."))
            active = record.payment_ids.filtered(lambda p: p.state != "cancel")
            if not active:
                raise UserError(
                    _("Create the payment(s) before confirming the payment.")
                )
            not_exported = active.filtered(
                lambda p: p.needs_bank_export and p.export_status != "exported"
            )
            if not_exported:
                raise UserError(
                    _(
                        "These payments have not left in an e-payment file yet: "
                        "%s. Put them in a file and mark it done before "
                        "confirming the payment."
                    )
                    % ", ".join(not_exported.mapped("name"))
                )
            # Every voucher raised by the authorisation was confirmed for the bank
            # there. One that reached the request another way — added by hand, or
            # unconfirmed to correct a coordinate and left that way — is confirmed
            # here instead: it is what gives it its number, and confirming it for a
            # bank says nothing this press does not already imply.
            active.filtered(
                lambda p: p.finance_state == "draft"
            ).action_confirm_for_bank()
            # Only the ones still waiting. Closing an e-payment file is itself
            # ยืนยันจ่ายสำเร็จ for the payees it carried, so by the time this press
            # happens most of a request is usually paid already — and ``_mark_paid``
            # refuses a voucher that is not ``confirmed``, so passing them all would
            # make this press fail on exactly the requests that had gone out
            # normally.
            active.filtered(
                lambda payment: payment.finance_state == "confirmed"
            )._mark_paid()
            # Usually a no-op by now: marking the last voucher paid crosses the
            # Hand-over on its own. It still matters for a request whose vouchers
            # were all paid before this press, where nothing was written and so
            # nothing fired.
            record._hand_over()
        return True

    def _hand_over(self):
        """The Hand-over: the request stops being the finance office's.

        Idempotent, and that is the point — it is reached two ways. Normally the
        last voucher turning paid brings the request across
        (``_try_hand_over_when_all_paid``); the finance office's own press calls it
        too, for the case where there was nothing left to mark. Filtering on the
        state it crosses *from* is what keeps the accounting office from getting the
        same Todo twice.
        """
        for record in self.filtered(lambda rec: rec.state == "payment_authorized"):
            record.state = "paid"
            record.activity_feedback([TO_PAY_ACTIVITY])
            # One Todo for the request, because the request is the document KMITL
            # navigates by — not twelve for twelve payees.
            record._schedule_payment_todo(TO_BOOK_ACTIVITY, ACCOUNTING_MAKER_GROUP)
        return True

    def _try_hand_over_when_all_paid(self):
        """Cross the Hand-over once every payee of this request has their money.

        A request's payees can span several หัวจ่าย, so its vouchers go out in as
        many e-payment files, and no two of those files need be the same officer's.
        Nobody is therefore in a position to say "all of them are paid" on behalf of
        the others — so nobody is asked to. Each officer closes the file they
        handled, each closed file pays the vouchers it carried, and the request
        crosses when the last of them lands. The officer who happens to be last
        brings it across without having to know they were.

        A voucher still at ``draft`` — added by hand and never confirmed for the
        bank — holds the request here. That is intended: it has not been paid and
        the accounting office has nothing to book for it. What says so is the
        finance office's own Todo, which stays open, and จ่ายแล้ว n/m on the
        request.
        """
        for record in self:
            if record.state != "payment_authorized":
                continue
            active = record.payment_ids.filtered(
                lambda payment: payment.state != "cancel"
            )
            if not active or active.filtered(
                lambda payment: payment.finance_state != "paid"
            ):
                continue
            record._hand_over()
        return True

    def action_submit_payments(self):
        """The accounting maker submits every voucher of a paid request at once.

        Their step is per voucher — correct the booking, then submit — but a request
        whose vouchers need no correction is the same press repeated, and the request
        is the document they navigate by. A voucher that does need work is opened
        from the queue and submitted on its own entry instead.

        Submitting is what asks the approver: ``account.move.action_submit`` puts the
        Todo in their inbox, so the makers' own Todo on the request is cleared here.
        """
        for record in self:
            if record.state != "paid":
                raise UserError(
                    _("Only a request the finance office has paid can be booked.")
                )
            active = record.payment_ids.filtered(lambda p: p.state != "cancel")
            drafts = active.move_id.filtered(lambda move: move.state == "draft")
            if not drafts:
                raise UserError(
                    _("Every voucher of %s is already submitted.") % record.display_name
                )
            result = drafts.action_submit()
            if isinstance(result, dict):
                # base_exception wants to show a popup, and a queue has nobody to
                # show it to: report it as the reason this request could not be
                # booked rather than leaving the vouchers silently in draft.
                raise UserError(
                    _(
                        "%s has vouchers with blocking exceptions. Open the entry "
                        "and submit it there to see them."
                    )
                    % record.display_name
                )
            record.activity_feedback([TO_BOOK_ACTIVITY])
        return True

    def action_submit_payments_batch(self):
        return self._payment_batch("action_submit_payments", "paid")

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
    # Payment creation (finance)
    # ------------------------------------------------------------------
    def action_create_payment(self):
        """The finance office's way back in when the authorisation raised nothing.

        Normally the vouchers already exist by the time the request reaches them —
        authorising it is what raises them (ADR-0006). This is what is left for
        the cases where it could not: a banking coordinate that was wrong at the
        time, a request authorized before this was built, or a batch that was
        cancelled and is wanted again.
        """
        self.ensure_one()
        payments = self._create_payments()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "domain": [("id", "in", payments.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def _create_payments(self):
        """Raise one numbered voucher per payee, confirmed for the bank.

        Confirming is part of raising them rather than a later errand: a file may
        only carry vouchers that can no longer change underneath it, so the gate
        the e-payment export reads and the moment the voucher is made are the same
        moment. It is also what gives each one its ใบสำคัญจ่าย number, which is
        why the chatter can name them.
        """
        self.ensure_one()
        if self.state != "payment_authorized":
            raise UserError(
                _("The disbursement must be authorized before creating the payment.")
            )
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
