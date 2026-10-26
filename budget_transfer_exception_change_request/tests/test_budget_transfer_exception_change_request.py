from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.budget_transfer_change_request.tests import (
    test_budget_transfer_change_request as change_request_tests,
)

RULE = "budget_transfer_exception_change_request.budget_transfer_excep_outstanding_change_requests"


@tagged("post_install", "-at_install")
class TestBudgetTransferExceptionChangeRequest(
    change_request_tests.TestBudgetTransferChangeRequest
):
    """ยืนยันตรวจสอบ waits until no Change request is outstanding (reuses the
    Change request fixtures)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The fixtures switch every transfer rule off; this one is under test.
        cls.env.ref(RULE).active = True

    def test_verify_waits_for_outstanding_requests(self):
        transfer = self._submitted_for_verify()
        request = self._ask(transfer)
        with self.assertRaisesRegex(ValidationError, "ยังมีข้อแก้ไขที่ค้างอยู่"):
            transfer.with_user(self.buddy).action_verify()
        # Answered is still outstanding: its author has to close it.
        self.env["change.request"].with_user(self.requestor).request_reply(
            request["id"], "แก้แล้ว"
        )
        with self.assertRaises(ValidationError):
            transfer.with_user(self.buddy).action_verify()
        self.env["change.request"].with_user(self.buddy).request_set_closed(
            request["id"], True
        )
        transfer.with_user(self.buddy).action_verify()
        self.assertEqual(transfer.state, "submitted")

    def test_confirm_again_with_answered_requests(self):
        """Back to the Buddy after a return: the requests are answered, not
        closed yet, and do not stop the requester's ยืนยัน."""
        transfer = self._submitted_for_verify()
        request = self._ask(transfer)
        self.env["budget.transfer.verify.return.wizard"].with_user(self.buddy).create(
            {"transfer_id": transfer.id}
        ).action_confirm()
        self.assertEqual(transfer.state, "draft")
        self.env["change.request"].with_user(self.requestor).request_reply(
            request["id"], "แก้แล้ว"
        )
        transfer.action_submit()
        self.assertEqual(transfer.state, "to_verify")

    def test_rule_switched_off(self):
        self.env.ref(RULE).active = False
        transfer = self._submitted_for_verify()
        self._ask(transfer)
        transfer.with_user(self.buddy).action_verify()
        self.assertEqual(transfer.state, "submitted")


# Run only the tests above, not the inherited ones again.
for _name in dir(change_request_tests.TestBudgetTransferChangeRequest):
    if _name.startswith("test_") and _name not in vars(
        TestBudgetTransferExceptionChangeRequest
    ):
        setattr(TestBudgetTransferExceptionChangeRequest, _name, None)
