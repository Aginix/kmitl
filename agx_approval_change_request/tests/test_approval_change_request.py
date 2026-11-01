from datetime import date

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

RULE = "agx_approval_change_request.excep_outstanding_change_requests"
SENT_BACK_RULE = "agx_approval_change_request.excep_sent_back_change_requests"


@tagged("post_install", "-at_install")
class TestApprovalChangeRequest(TransactionCase):
    """ผู้ตรวจสอบคำขอ details what to fix as Change requests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.requestor = new_test_user(
            cls.env, login="cr_requestor", groups="agx_approval.group_approval_user"
        )
        cls.verifier = new_test_user(
            cls.env, login="cr_verifier", groups="agx_approval.group_approval_verify"
        )
        cls.verifier2 = new_test_user(
            cls.env, login="cr_verifier2", groups="agx_approval.group_approval_verify"
        )
        today = date.today()
        fiscal_year = cls.env.company.find_daterange_fy(today) or cls.env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY test",
                "date_from": today.replace(month=1, day=1),
                "date_to": today.replace(month=12, day=31),
            }
        )
        cls.request = cls.env["approval.request"].create(
            {
                "category_id": cls.env.ref(
                    "agx_approval.approval_category_5102010000"
                ).id,
                "user_id": cls.requestor.id,
                "owner_id": cls.env["hr.employee"]
                .create({"name": "Requestor", "user_id": cls.requestor.id})
                .id,
                "account_fiscal_year_id": fiscal_year.id,
            }
        )
        cls.request.state = "to_verify"
        if cls.request._fields.get("operating_unit_id"):
            # agx_approval_operating_unit: the users work in the request's OU.
            (cls.requestor | cls.verifier | cls.verifier2).write(
                {"assigned_operating_unit_ids": [(4, cls.request.operating_unit_id.id)]}
            )
        # The fixture has no lines nor participants: only the rule under test
        # (and the ตีกลับ markers, which are never evaluated).
        keep = cls.env.ref(RULE) | cls.request._sent_back_rules()
        cls.env["exception.rule"].search(
            [("model", "=", "approval.request"), ("id", "not in", keep.ids)]
        ).active = False

    def _ask(self, text="ยอดเงินไม่ตรงกับเอกสาร", user=None):
        return (
            self.env["change.request"]
            .with_user(user or self.verifier)
            .request_create(self.request._name, self.request.id, text, [])
        )

    def _wizard(self, reason=False):
        return (
            self.env["approval.request.send.back.confirm"]
            .with_user(self.verifier)
            .create({"request_id": self.request.id, "reason": reason})
        )

    def test_verifier_closes_on_behalf(self):
        Request = self.env["change.request"]
        # Asked by the verifier: the requestor may not close it.
        with self.assertRaises(AccessError):
            Request.with_user(self.requestor).request_set_closed(
                self._ask()["id"], True
            )
        # Asked by the requestor: another verifier closes it on their behalf.
        request = self._ask(user=self.requestor)
        closed = Request.with_user(self.verifier2).request_set_closed(
            request["id"], True
        )
        self.assertEqual(closed["state"], "closed")

    def test_send_back_lists_outstanding_requests(self):
        self._ask()
        wizard = self._wizard()
        self.assertIn("ยอดเงินไม่ตรงกับเอกสาร", wizard.outstanding_requests)
        # No reason needed while requests are outstanding.
        wizard.action_confirm()
        self.assertEqual(self.request.state, "draft")

    def test_send_back_marks_outstanding_requests(self):
        marker = self.env.ref(SENT_BACK_RULE)
        self._ask()
        self._wizard().action_confirm()
        self.assertIn(marker, self.request.exception_ids)
        # Not evaluated: resubmitting is not held up, and clears the marker.
        self.assertTrue(self.request.sudo().action_to_verify())
        self.assertEqual(self.request.state, "to_verify")
        self.assertNotIn(marker, self.request.exception_ids)

    def test_send_back_without_requests_leaves_no_marker(self):
        self._wizard(reason="แก้ไขเอกสารแนบ").action_confirm()
        self.assertEqual(self.request.state, "draft")
        self.assertNotIn(self.env.ref(SENT_BACK_RULE), self.request.exception_ids)

    def test_send_back_needs_a_reason_without_requests(self):
        with self.assertRaises(UserError):
            self._wizard().action_confirm()
        self.assertEqual(self.request.state, "to_verify")

    def test_verify_waits_for_outstanding_requests(self):
        request = self._ask()
        action = self.request.with_user(self.verifier).action_confirm_verify()
        self.assertIsInstance(action, dict)  # the exception popup
        self.assertEqual(self.request.state, "to_verify")
        # Answered is still outstanding: its author has to close it.
        Request = self.env["change.request"]
        Request.with_user(self.requestor).request_reply(request["id"], "แก้แล้ว")
        self.request.with_user(self.verifier).action_confirm_verify()
        self.assertEqual(self.request.state, "to_verify")
        Request.with_user(self.verifier).request_set_closed(request["id"], True)
        self.request.with_user(self.verifier).action_confirm_verify()
        self.assertEqual(self.request.state, "to_commit")

    def test_rule_switched_off(self):
        self.env.ref(RULE).active = False
        self._ask()
        self.request.with_user(self.verifier).action_confirm_verify()
        self.assertEqual(self.request.state, "to_commit")
