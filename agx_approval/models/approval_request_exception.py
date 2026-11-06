from odoo import api, fields, models

# ตีกลับ markers, keyed by the step that sent the request back. The send-back
# flow links them itself (_mark_sent_back) and any later state change clears
# them. Detection never evaluates them: it would unlink them, and pop them up
# on the very resubmission that should clear them.
SENT_BACK_RULES = {
    "to_verify": "agx_approval.excep_sent_back_verify",
    "to_commit": "agx_approval.excep_sent_back_commit",
}


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _inherit = ["approval.request", "base.exception"]
    _order = "main_exception_id asc, name desc"

    @api.model
    def _reverse_field(self):
        return "approval_request_ids"

    def _sent_back_rules(self):
        return self.env["exception.rule"].browse(
            [self.env.ref(xmlid).id for xmlid in SENT_BACK_RULES.values()]
        )

    def _rule_domain(self):
        # tuple: base_exception caches rules keyed on the (hashable) domain
        return super()._rule_domain() + [
            ("id", "not in", tuple(self._sent_back_rules().ids))
        ]

    def _mark_sent_back(self, step):
        """Show ตีกลับ from ``step`` (to_verify / to_commit) in ข้อผิดพลาด."""
        self.exception_ids = [(4, self.env.ref(SENT_BACK_RULES[step]).id)]

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            rules = self._sent_back_rules()
            marked = self.filtered(lambda r: r.exception_ids & rules)
            if marked:
                marked.write({"exception_ids": [(3, rule.id) for rule in rules]})
        return res

    # -- exception.rule helpers --------------------------------------------
    # Called from by_py_code rules in data/approval_request_exception_data.xml.
    # The rules stay one-liners: the logic lives here where it is readable and
    # not subject to safe_eval's restricted namespace.

    def _exception_submit_date_outside_fy(self):
        """True when today — the date about to be stamped as วันที่ส่งคำขอ — falls
        outside the ปีงบประมาณ the request declares.

        Drafting ahead is fine (pick next year's ปีงบ whenever); *submitting* ahead
        is not. The submit date is what the ใบจอง and every downstream document key
        off, so it has to sit inside the year whose money is being reserved — a
        request filed in advance simply waits in draft until that year opens.

        Checked against today rather than ``self.date`` because the stamp happens
        in the same transition, after ``detect_exceptions`` has already run.
        """
        self.ensure_one()
        fy = self.account_fiscal_year_id
        if not fy:
            # required=True already covers a missing year; don't double-report.
            return False
        today = fields.Date.context_today(self)
        return not (fy.date_from <= today <= fy.date_to)

    def _exception_draw_exceeds_available(self):
        """True when the plan total (แผนค่าใช้จ่าย) would draw more than the
        picked ใบจองงบประมาณ currently has left (``available_to_obligate`` —
        reserved minus already-obligated). False when reserving new instead of
        drawing (no reservation_commitment_id), since a new commitment's own
        availability is checked separately (``_check_budget_availability``).

        A gate on the *draw*, not a standing invariant: once the slip is drawn
        (``budget_commitment_id`` is that slip) the check goes quiet. Every
        later ``detect_exceptions()`` would otherwise re-test the *plan*
        total against an availability that legitimately shrank meanwhile (a
        shared project slip drawn by sibling requests), blocking a request whose
        แผน can no longer be edited (is_plan_editable) and whose actual spend may
        well fit. Obligate-level availability is enforced by budget.controller at
        disbursement.
        """
        self.ensure_one()
        commitment = self.reservation_commitment_id
        if not commitment or self.budget_commitment_id == commitment:
            return False
        return (
            self.currency_id.compare_amounts(
                self.total_amount, commitment.available_to_obligate
            )
            > 0
        )

    def _exception_plan_amount_mismatch(self):
        """True when an itemized request's lines (category with Expense Items)
        do not add up to its จำนวนเงิน (``plan_amount``) — the ceiling the
        requester declared up front. Without Expense Items the amount is
        mirrored onto the one line, so it can never mismatch."""
        self.ensure_one()
        if not self.has_expense_items:
            return False
        return bool(
            self.currency_id.compare_amounts(self.total_amount, self.plan_amount)
        )

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "agx_approval.action_approval_request_exception_confirm"
        )

    def _popup_exceptions(self):
        action = super()._popup_exceptions()
        action["context"]["agx_exception_action"] = self.env.context.get(
            "agx_exception_action", False
        )
        return action
