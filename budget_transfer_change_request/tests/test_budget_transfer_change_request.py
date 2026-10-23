from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.budget_transfer_verify.models.budget_transfer import CORRECT_ACTIVITY
from odoo.addons.budget_transfer_verify.tests import (
    test_budget_transfer_verify as verify_tests,
)


@tagged("post_install", "-at_install")
class TestBudgetTransferChangeRequest(verify_tests.TestBudgetTransferVerify):
    """The Buddy details what to fix as Change requests; ยืนยันตรวจสอบ waits
    until none is outstanding (reuses the Buddy Verification fixtures)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A copy of production carries exception rules on transfers that stop
        # the fixture's ยืนยัน short of รอตรวจสอบ; they are not tested here.
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].search(
                [("model", "=", "budget.transfer")]
            ).active = False

    def _ask(self, transfer, text="ยอดโอนไม่ตรงกับตาราง", user=None):
        return (
            self.env["change.request"]
            .with_user(user or self.buddy)
            .request_create(transfer._name, transfer.id, text, [])
        )

    def test_verify_waits_for_outstanding_requests(self):
        transfer = self._submitted_for_verify()
        request = self._ask(transfer)
        with self.assertRaisesRegex(UserError, "ยอดโอนไม่ตรงกับตาราง"):
            transfer.with_user(self.buddy).action_verify()
        # Answered is still outstanding: its author has to close it.
        self.env["change.request"].with_user(self.requestor).request_reply(
            request["id"], "แก้แล้ว"
        )
        with self.assertRaises(UserError):
            transfer.with_user(self.buddy).action_verify()
        self.env["change.request"].with_user(self.buddy).request_set_closed(
            request["id"], True
        )
        transfer.with_user(self.buddy).action_verify()
        self.assertEqual(transfer.state, "submitted")

    def test_covering_buddy_closes_on_behalf(self):
        transfer = self._submitted_for_verify()
        # Asked by someone else who reads the transfer.
        request = self._ask(transfer, user=self.requestor)
        Request = self.env["change.request"]
        with self.assertRaises(Exception):
            Request.with_user(self.outsider).request_set_closed(request["id"], True)
        closed = Request.with_user(self.buddy2).request_set_closed(request["id"], True)
        self.assertEqual(closed["state"], "closed")
        transfer.with_user(self.buddy).action_verify()
        self.assertEqual(transfer.state, "submitted")

    def test_return_lists_outstanding_requests(self):
        transfer = self._submitted_for_verify()
        self._ask(transfer)
        wizard = (
            self.env["budget.transfer.verify.return.wizard"]
            .with_user(self.buddy)
            .create({"transfer_id": transfer.id})
        )
        self.assertIn("ยอดโอนไม่ตรงกับตาราง", wizard.outstanding_requests)
        # No reason needed while requests are outstanding.
        wizard.action_confirm()
        self.assertEqual(transfer.state, "draft")
        todo = transfer.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref(CORRECT_ACTIVITY)
        )
        self.assertEqual(todo.user_id, self.requestor)
        self.assertIn("ยอดโอนไม่ตรงกับตาราง", todo.note)

    def test_return_needs_a_reason_without_requests(self):
        transfer = self._submitted_for_verify()
        wizard = (
            self.env["budget.transfer.verify.return.wizard"]
            .with_user(self.buddy)
            .create({"transfer_id": transfer.id})
        )
        with self.assertRaises(UserError):
            wizard.action_confirm()


# Run only the tests above, not the inherited Buddy Verification ones again
# (the base class is reached through its module for the same reason).
for _name in dir(verify_tests.TestBudgetTransferVerify):
    if _name.startswith("test_") and _name not in vars(TestBudgetTransferChangeRequest):
        setattr(TestBudgetTransferChangeRequest, _name, None)
