# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# States in which a loan is a live debt the borrower still holds — the debt
# starts at effective_date (waiting_transfer is pre-debt, done/cancel are
# closed). Reporting and returning both happen freely within in_progress, so
# it's the only debtor state. Countdown, followup list and digest key off it.
DEBTOR_STATES = ("in_progress",)

# Generic "To Do" activity type — matched together with its summary so a
# weekly re-run of the digest cron never piles up duplicate reminders on the
# same loan (same idiom as advance.payment._workflow_activities, ADR-0013).
FOLLOWUP_ACTIVITY_XMLID = "mail.mail_activity_data_todo"


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    days_to_return = fields.Integer(
        string="วันคงเหลือก่อนครบกำหนดคืน",
        compute="_compute_days_to_return",
        store=True,
    )

    days_to_return_display = fields.Char(
        string="วันคงเหลือก่อนครบกำหนดคืน",
        compute="_compute_days_to_return_display",
        store=False,
    )

    return_range = fields.Selection(
        [
            ("overdue", "เกินกำหนด"),
            ("0-7", "0-7 วัน"),
            ("8-15", "8-15 วัน"),
            ("16-30", "16-30 วัน"),
            ("30+", "มากกว่า 30 วัน"),
        ],
        string="ช่วงวันครบกำหนดคืน",
        compute="_compute_return_range",
        store=True,
    )

    is_overdue = fields.Boolean(
        string="เกินกำหนดคืน",
        compute="_compute_is_overdue",
        store=True,
    )

    @api.depends("return_due_date", "state")
    def _compute_days_to_return(self):
        """Countdown to `return_due_date`; 0 outside the debtor window."""
        today = fields.Date.today()
        for rec in self:
            if rec.state in DEBTOR_STATES and rec.return_due_date:
                rec.days_to_return = (rec.return_due_date - today).days
            else:
                rec.days_to_return = 0

    @api.depends("days_to_return", "return_due_date", "state")
    def _compute_days_to_return_display(self):
        """Text form of `days_to_return` for the tree column; blank when
        there's nothing to count down to."""
        for rec in self:
            rec.days_to_return_display = (
                str(rec.days_to_return)
                if rec.state in DEBTOR_STATES and rec.return_due_date
                else ""
            )

    @api.depends("days_to_return", "return_due_date", "state")
    def _compute_return_range(self):
        """Bucket a debtor loan by how close it is to (or past) its due
        date, for the followup list's grouping/decoration."""
        for rec in self:
            if rec.state not in DEBTOR_STATES or not rec.return_due_date:
                rec.return_range = False
                continue
            days = rec.days_to_return
            if days < 0:
                rec.return_range = "overdue"
            elif days <= 7:
                rec.return_range = "0-7"
            elif days <= 15:
                rec.return_range = "8-15"
            elif days <= 30:
                rec.return_range = "16-30"
            else:
                rec.return_range = "30+"

    @api.depends("days_to_return", "return_due_date", "state")
    def _compute_is_overdue(self):
        """Convenience boolean for tree decoration/search — past due and
        still an open debt."""
        for rec in self:
            rec.is_overdue = (
                rec.state in DEBTOR_STATES
                and bool(rec.return_due_date)
                and rec.days_to_return < 0
            )

    @api.model
    def _cron_recompute_return_days(self):
        """`days_to_return` is stored but computed against "today", so it
        goes stale a day after it was last written — recompute it (and the
        fields derived from it) daily, same reasoning as
        purchase_guarantee_expiration.action_recompute_expire."""
        records = self.search(
            [("state", "in", DEBTOR_STATES), ("return_due_date", "!=", False)]
        )
        records._compute_days_to_return()
        records._compute_return_range()
        records._compute_is_overdue()

    @api.model
    def _followup_notify_before_days(self):
        """Days-before-due-date threshold, configurable in Settings."""
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("advance_payment_followup.notify_before_days", default=7)
        )

    def _domain_followup_digest(self):
        """Debtor loans due within the configured window (negative
        `days_to_return` — already overdue — always qualifies)."""
        return [
            ("state", "in", DEBTOR_STATES),
            ("return_due_date", "!=", False),
            ("days_to_return", "<=", self._followup_notify_before_days()),
        ]

    def _send_followup_digest(self, template, partner, loans):
        """Render `template` against `partner` with `loans` in the QWeb
        rendering scope and send a single email — a standard mail.template
        renders once per record, which can't aggregate several loans into
        one digest message. One partner's bad data (e.g. a broken template
        override) must not stop the rest of the digest from going out."""
        if not partner or not partner.email:
            return
        try:
            body = template._render_template(
                template.body_html,
                "res.partner",
                partner.ids,
                engine="qweb",
                add_context={"followup_loans": loans},
                post_process=True,
            )[partner.id]
            subject = template._render_template(
                template.subject, "res.partner", partner.ids
            )[partner.id]
            self.env["mail.mail"].sudo().create(
                {
                    "subject": subject,
                    "body_html": body,
                    "recipient_ids": [(6, 0, partner.ids)],
                    "auto_delete": True,
                }
            )
        except Exception:
            _logger.warning(
                "Failed to send advance payment followup digest to %s",
                partner.name,
                exc_info=True,
            )

    def _followup_activity_summary(self):
        """Dedup key for the followup To-Do. Deliberately excludes
        `return_due_date`: the date is carried on `date_deadline` instead, so
        a due-date edit updates the existing To-Do in place (see
        `_schedule_followup_activities`) rather than orphaning it under a
        summary that no longer matches."""
        self.ensure_one()
        return _("ติดตามลูกหนี้เงินยืม %s", self.name)

    def _schedule_followup_activities(self):
        """Raise one To-Do per loan on its loan officer, deduped by
        (activity type, summary). A match is refreshed in place — assignee
        and due date included — so reassigning the loan officer or editing
        `return_due_date` doesn't leave a stale To-Do behind."""
        activity_type = self.env.ref(FOLLOWUP_ACTIVITY_XMLID)
        for rec in self:
            if not rec.loan_verifier_id:
                continue
            summary = rec._followup_activity_summary()
            existing = rec.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
                and a.summary == summary
            )
            if existing:
                existing.sudo().write(
                    {
                        "user_id": rec.loan_verifier_id.id,
                        "date_deadline": rec.return_due_date,
                    }
                )
                continue
            rec.activity_schedule(
                FOLLOWUP_ACTIVITY_XMLID,
                user_id=rec.loan_verifier_id.id,
                summary=summary,
                date_deadline=rec.return_due_date,
            )

    @api.model
    def _close_stale_followup_activities(self, eligible_loans):
        """Close the followup To-Do on any loan that no longer qualifies for
        one (paid off/cancelled, or its due date moved outside the notify
        window) — otherwise it sits on the officer's desk forever pointing
        at a loan the tracker no longer considers a debtor."""
        activity_type = self.env.ref(FOLLOWUP_ACTIVITY_XMLID)
        stale = self.env["mail.activity"].sudo().search(
            [
                ("activity_type_id", "=", activity_type.id),
                ("res_model", "=", self._name),
                ("res_id", "not in", eligible_loans.ids),
                ("summary", "like", "ติดตามลูกหนี้เงินยืม%"),
            ]
        )
        if stale:
            stale.action_feedback(
                feedback=_("ปิดอัตโนมัติ: ไม่อยู่ในเกณฑ์ติดตามลูกหนี้แล้ว")
            )

    @api.model
    def _cron_send_followup_digest(self):
        """Weekly: email a digest to every borrower/officer with a loan due
        soon or overdue, raise/refresh their followup To-Do, and close any
        To-Do left over from a loan that has since dropped out of scope."""
        loans = self.search(self._domain_followup_digest())
        self._close_stale_followup_activities(loans)
        if not loans:
            return

        borrower_template = self.env.ref(
            "advance_payment_followup.mail_template_followup_borrower"
        )
        officer_template = self.env.ref(
            "advance_payment_followup.mail_template_followup_officer"
        )

        loans_by_borrower = {}
        loans_by_officer = {}
        for loan in loans:
            borrower = loan.employee_id.user_id.partner_id
            if borrower:
                loans_by_borrower.setdefault(borrower, self.browse())
                loans_by_borrower[borrower] |= loan
            officer = loan.loan_verifier_id.partner_id
            if officer:
                loans_by_officer.setdefault(officer, self.browse())
                loans_by_officer[officer] |= loan

        for partner, partner_loans in loans_by_borrower.items():
            self._send_followup_digest(borrower_template, partner, partner_loans)
        for partner, partner_loans in loans_by_officer.items():
            self._send_followup_digest(officer_template, partner, partner_loans)

        loans._schedule_followup_activities()
