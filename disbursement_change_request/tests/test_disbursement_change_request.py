# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestDisbursementChangeRequest(TwoApproverCommon):
    """The officer details what to fix as Change requests."""

    def _ask(self, dr, text="ยอดเงินไม่ตรงกับใบเสร็จ", user=None):
        return (
            self.env["change.request"]
            .with_user(user or self.officer)
            .request_create(dr._name, dr.id, text, [])
        )

    def test_validate_waits_for_outstanding_requests(self):
        dr = self._make_signed_dr()
        request = self._ask(dr)
        with self.assertRaises(UserError):
            dr.with_user(self.officer).action_validate()
        self.env["change.request"].with_user(self.officer).request_set_closed(
            request["id"], True
        )
        dr.with_user(self.officer).action_validate()
        self.assertEqual(dr.verifier_id, self.officer)

    def test_rule_switched_off_lets_validate_through(self):
        dr = self._make_signed_dr()
        self._ask(dr)
        self.env.ref(
            "disbursement_change_request.excep_disbursement_outstanding_change_requests"
        ).active = False
        dr.with_user(self.officer).action_validate()
        self.assertEqual(dr.verifier_id, self.officer)

    def test_officer_closes_on_behalf(self):
        dr = self._make_signed_dr()
        # Asked by someone else who reads the request.
        request = self._ask(dr, user=self.rector)
        Request = self.env["change.request"]
        with self.assertRaises(Exception):
            Request.with_user(self.finance).request_set_closed(request["id"], True)
        closed = Request.with_user(self.officer).request_set_closed(request["id"], True)
        self.assertEqual(closed["state"], "closed")

    def test_return_lists_outstanding_requests(self):
        dr = self._make_signed_dr()
        self._ask(dr)
        wizard = (
            self.env["disbursement.return.request.wizard"]
            .with_user(self.officer)
            .create({"request_id": dr.id})
        )
        self.assertIn("ยอดเงินไม่ตรงกับใบเสร็จ", wizard.outstanding_requests)
        # No reason needed while requests are outstanding.
        wizard.action_return()
        self.assertEqual(dr.state, "draft")
        self.assertTrue(dr.returned_for_edit)
        todo = dr.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref("mail.mail_activity_data_todo")
        )
        self.assertIn("ยอดเงินไม่ตรงกับใบเสร็จ", todo.note)
        self.assertIn(
            self.env.ref(
                "disbursement_change_request."
                "excep_disbursement_sent_back_change_requests"
            ),
            dr.exception_ids,
        )

    def test_return_needs_a_reason_without_requests(self):
        dr = self._make_signed_dr()
        wizard = (
            self.env["disbursement.return.request.wizard"]
            .with_user(self.officer)
            .create({"request_id": dr.id})
        )
        with self.assertRaises(UserError):
            wizard.action_return()

    def test_return_with_a_reason_only_is_not_marked_for_requests(self):
        dr = self._make_signed_dr()
        self.env["disbursement.return.request.wizard"].with_user(self.officer).create(
            {"request_id": dr.id, "reason": "แก้วันที่"}
        ).action_return()
        self.assertEqual(
            dr.exception_ids, self.env.ref("disbursement.excep_disbursement_sent_back")
        )
