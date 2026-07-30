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
    # Editable alias of line_ids for the Payment page: the base line_ids
    # one2many is readonly after draft (READONLY_STATES), but the auditor must
    # set the per-line payment method at bills_posted.
    payment_line_ids = fields.One2many(
        comodel_name="disbursement.request.line",
        inverse_name="request_id",
        string="Payment Lines",
        copy=False,
    )

    @api.onchange("payment_subject_id")
    def _onchange_payment_subject_id(self):
        """Default every line's method from the subject; the auditor then
        adjusts only the exception lines."""
        if self.payment_subject_id:
            self.line_ids.update(
                {"payment_method": self.payment_subject_id.default_method}
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
        # bill posts) opens the payment-execution phase: notify the auditors.
        if vals.get("state") == "bills_posted":
            self._schedule_payment_todo(TO_AUDIT_ACTIVITY, AUDITOR_GROUP)
        return res

    # ------------------------------------------------------------------
    # Payment classification helpers
    # ------------------------------------------------------------------
    def _resolve_line_journal(self, line):
        """Return the paying journal (หัวจ่าย) for a request line.

        Cheque lines draw on the journal configured on the 'จ่ายเช็ค' payment
        type (subjects carry no paying bank for cheques); the subject's main
        journal is a fallback. Transfer lines pay from the subject's main
        journal under the ``fixed`` policy, or — under ``payee_bank`` — from
        the institute's bank journal at the payee's own bank, matched by the
        bank behind each journal's account. Returns an empty recordset when no
        journal can be determined.
        """
        self.ensure_one()
        subject = self.payment_subject_id
        Journal = self.env["account.journal"]
        if not subject:
            return Journal
        company = self.company_id
        if line.payment_method == "cheque":
            cheque_type = self.env.ref(
                "finance_kmitl.payment_type_cheque_outbound",
                raise_if_not_found=False,
            )
            cheque_journal = cheque_type.journal_id if cheque_type else Journal
            return (
                cheque_journal.filtered(lambda j: j.company_id == company)
                or subject.journal_id.filtered(
                    lambda j: j.company_id == company
                )
            )
        if subject.bank_policy == "fixed":
            return subject.journal_id.filtered(
                lambda j: j.company_id == company
            )
        payee_bank = line.partner_bank_id.bank_id
        if not payee_bank:
            return Journal
        return Journal.search(
            [
                ("type", "=", "bank"),
                ("company_id", "=", self.company_id.id),
                ("bank_account_id.bank_id", "=", payee_bank.id),
            ],
            limit=1,
        )

    def _check_payment_classification(self):
        """Validate the auditor's classification before confirming the audit.

        Fills empty line methods from the subject default, then blocks with an
        actionable error listing the offending payees when the classification
        cannot drive payment creation.
        """
        for record in self:
            subject = record.payment_subject_id
            if not subject:
                raise UserError(
                    _("Select the payment subject (เรื่องที่จ่าย) before "
                      "confirming the audit.")
                )
            record.line_ids.filtered(lambda l: not l.payment_method).update(
                {"payment_method": subject.default_method}
            )

            cheque_lines = record.line_ids.filtered(
                lambda l: l.payment_method == "cheque"
            )
            transfer_lines_all = record.line_ids.filtered(
                lambda l: l.payment_method == "transfer"
            )
            # A cheque subject carries no paying bank at all, so it cannot
            # drive transfers — the auditor must keep its lines on cheque.
            if subject.default_method == "cheque" and transfer_lines_all:
                raise UserError(
                    _(
                        "Payment subject '%(subject)s' is a cheque subject "
                        "(no paying bank configured) — switch these transfer "
                        "lines back to cheque: %(payees)s",
                        subject=subject.name,
                        payees=", ".join(
                            sorted(set(
                                transfer_lines_all.mapped("partner_id.name")
                            ))
                        ),
                    )
                )
            if (
                transfer_lines_all
                and subject.bank_policy == "fixed"
                and not subject.journal_id
            ):
                raise UserError(
                    _(
                        "Payment subject '%s' has no main paying journal "
                        "(หัวจ่ายหลัก) configured for transfers. Set it in "
                        "Finance ▸ Settings ▸ Payment Subjects first."
                    )
                    % subject.name
                )
            if cheque_lines and not record._resolve_line_journal(
                cheque_lines[0]
            ):
                raise UserError(
                    _(
                        "No journal configured for cheque payments. Set the "
                        "journal on the 'จ่ายเช็ค' payment type (Finance ▸ "
                        "Settings ▸ Payment Types) first."
                    )
                )

            # One bill per payee, paid in full by one payment — so all lines
            # of the same payee must share one method and one bank account.
            lines_by_partner = record._lines_by_partner()
            mixed = [
                partner.name
                for partner, lines in lines_by_partner.items()
                if len(set(lines.mapped("payment_method"))) > 1
            ]
            if mixed:
                raise UserError(
                    _(
                        "Payees with mixed payment methods (each payee must "
                        "use a single method): %s"
                    )
                    % ", ".join(mixed)
                )
            mixed_banks = [
                partner.name
                for partner, lines in lines_by_partner.items()
                if len(lines.mapped("partner_bank_id")) > 1
            ]
            if mixed_banks:
                raise UserError(
                    _(
                        "Payees with more than one bank account on their lines "
                        "(the bill and its payment can only carry one, so pick "
                        "a single account per payee): %s"
                    )
                    % ", ".join(mixed_banks)
                )

            transfer_lines = record.line_ids.filtered(
                lambda l: l.payment_method == "transfer"
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

            unmatched = transfer_lines.filtered(
                lambda l: not record._resolve_line_journal(l)
            )
            if unmatched:
                raise UserError(
                    _(
                        "Payees whose bank cannot be matched to a paying "
                        "journal (switch them to cheque or fix the bank "
                        "account): %s"
                    )
                    % ", ".join(sorted(set(unmatched.mapped("partner_id.name"))))
                )
        return True

    def _lines_by_partner(self):
        """Group request lines by payee partner (mirrors the bill grouping)."""
        self.ensure_one()
        grouped = {}
        for line in self.line_ids:
            grouped.setdefault(
                line.partner_id, self.env["disbursement.request.line"]
            )
            grouped[line.partner_id] |= line
        return grouped

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
    # Payment creation (finance)
    # ------------------------------------------------------------------
    def action_create_payment(self):
        """Create draft payments from the DR, one per posted unpaid bill."""
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
        posted_bills = self.bill_ids.filtered(lambda b: b.state == "posted")
        partial_bills = posted_bills.filtered(
            lambda b: b.payment_state == "partial"
        )
        if partial_bills:
            raise UserError(
                _(
                    "Partial payment is not supported. Bill(s) %s are already "
                    "partially paid."
                )
                % ", ".join(partial_bills.mapped("name"))
            )
        unpaid_bills = posted_bills.filtered(
            lambda b: b.payment_state == "not_paid"
        )
        if not unpaid_bills:
            raise UserError(_("No posted unpaid bills to pay."))

        # Journal (หัวจ่าย) and operation type are driven by the auditor's
        # classification: subject bank policy + per-line method.
        self._check_payment_classification()
        transfer_type = self.env.ref(
            "finance_kmitl.payment_type_normal_outbound",
            raise_if_not_found=False,
        )
        cheque_type = self.env.ref(
            "finance_kmitl.payment_type_cheque_outbound",
            raise_if_not_found=False,
        )
        lines_by_partner = self._lines_by_partner()

        payments = self.env["account.payment"]
        for bill in unpaid_bills:
            partner_lines = lines_by_partner.get(bill.partner_id)
            if not partner_lines:
                raise UserError(
                    _("No request lines found for payee %s.")
                    % bill.partner_id.name
                )
            method = partner_lines[0].payment_method or "transfer"
            journal = self._resolve_line_journal(partner_lines[0])
            if not journal:
                raise UserError(
                    _("No paying journal could be resolved for payee %s.")
                    % bill.partner_id.name
                )
            payment_type = cheque_type if method == "cheque" else transfer_type
            payable_lines = bill.line_ids.filtered(
                lambda l: l.account_type == "liability_payable"
                and not l.reconciled
            )
            amount = abs(bill.amount_residual)

            wht_lines = bill.line_ids.filtered("wht_tax_id")
            write_off_line_vals = []
            if wht_lines:
                deduction_list, amount_wht = (
                    wht_lines._prepare_deduction_list(
                        fields.Date.context_today(self),
                        bill.currency_id,
                    )
                )
                if deduction_list and amount_wht:
                    amount -= amount_wht
                    for deduct in deduction_list:
                        write_off_line_vals.append({
                            "name": deduct["name"],
                            "account_id": deduct["account_id"],
                            "partner_id": bill.partner_id.id,
                            "currency_id": bill.currency_id.id,
                            "amount_currency": -deduct["amount"],
                            "balance": -deduct["amount"],
                            "wht_tax_id": deduct["wht_tax_id"],
                            "tax_base_amount": deduct["wht_amount_base"],
                        })

            payment_vals = {
                "disbursement_request_id": self.id,
                "partner_id": bill.partner_id.id,
                "amount": amount,
                "currency_id": bill.currency_id.id,
                "journal_id": journal.id,
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
