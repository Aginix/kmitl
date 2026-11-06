from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.advance_payment_return_exception.tests.test_sent_back_exception import (  # noqa: B950
    SentBackCommon,
)


@tagged("post_install", "-at_install")
class TestAdvancePaymentChangeRequest(SentBackCommon):
    def _ask(self, loan, user, text="แนบใบเสนอราคาไม่ครบ"):
        return (
            self.env["change.request"]
            .with_user(user)
            .request_create(loan._name, loan.id, text, [])
        )

    def _to_verify(self):
        loan = self._submitted()
        loan.action_endorse()
        self.assertEqual(loan.state, "to_verify")
        return loan

    def test_verify_waits_for_outstanding_requests(self):
        loan = self._to_verify()
        request = self._ask(loan, self.officer)
        with self.assertRaises(UserError):
            loan.with_user(self.officer).action_verify()
        self.env["change.request"].with_user(self.officer).request_set_closed(
            request["id"], True
        )
        loan.with_user(self.officer).action_verify()
        self.assertNotEqual(loan.state, "to_verify")

    def test_rule_switched_off_lets_verify_through(self):
        loan = self._to_verify()
        self._ask(loan, self.officer)
        self.env.ref(
            "advance_payment_change_request."
            "excep_advance_payment_outstanding_change_requests"
        ).active = False
        loan.with_user(self.officer).action_verify()
        self.assertNotEqual(loan.state, "to_verify")

    def test_endorse_is_not_held_up(self):
        loan = self._submitted()
        self._ask(loan, self.officer)
        loan.with_user(self.supervisor).action_endorse()
        self.assertEqual(loan.state, "to_verify")

    def test_officer_closes_on_behalf_at_verify(self):
        loan = self._submitted()
        request = self._ask(loan, self.supervisor)
        Request = self.env["change.request"]
        with self.assertRaises(Exception):
            Request.with_user(self.officer).request_set_closed(request["id"], True)
        loan.action_endorse()
        closed = Request.with_user(self.officer).request_set_closed(request["id"], True)
        self.assertEqual(closed["state"], "closed")

    def test_send_back_lists_requests_and_flags(self):
        loan = self._to_verify()
        self._ask(loan, self.officer)
        loan.with_user(self.officer).action_reset_to_draft()
        flag = self.env.ref(
            "advance_payment_change_request."
            "excep_advance_payment_sent_back_change_requests"
        )
        self.assertIn(flag, loan.exception_ids)
        self.assertIn(self.marker, loan.exception_ids)
        self.assertTrue(
            any("แนบใบเสนอราคาไม่ครบ" in (m.body or "") for m in loan.message_ids)
        )
        # Resubmitting clears both flags.
        loan.action_submit()
        self.assertFalse(loan.exception_ids & (flag | self.marker))

    def test_send_back_without_requests_sets_no_extra_flag(self):
        loan = self._to_verify()
        loan.with_user(self.officer).action_reset_to_draft()
        flag = self.env.ref(
            "advance_payment_change_request."
            "excep_advance_payment_sent_back_change_requests"
        )
        self.assertNotIn(flag, loan.exception_ids)
