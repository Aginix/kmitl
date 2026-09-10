from odoo import api, fields, models


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _inherit = ["approval.request", "base.exception"]
    _order = "main_exception_id asc, name desc"

    @api.model
    def _reverse_field(self):
        return "approval_request_ids"

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
        later ``detect_exceptions()`` — notably agx_approval_disbursement's
        action_create_disbursement_request — would otherwise re-test the *plan*
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
