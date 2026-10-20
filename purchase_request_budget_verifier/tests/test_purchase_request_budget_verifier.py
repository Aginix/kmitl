from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestBudgetVerifier(TransactionCase):
    """ผู้ยืนยันงบประมาณ พ.1 (ADR-0012): required at ตรวจสอบ, gets the
    to_verify_budget Todo instead of the role, which is done only when they
    move the request on and withdrawn otherwise."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ou = cls.env.ref("operating_unit.main_operating_unit")
        user = "purchase_request.group_purchase_request_user"
        verify = "purchase_request_kmitl.group_purchase_request_verify"
        commit = "purchase_request_budget.group_purchase_request_budget_commit"
        cls.requester = cls._user("pr_bver_requester", user)
        cls.verifier = cls._user("pr_bver_verifier", f"{user},{verify}")
        cls.committer = cls._user("pr_bver_committer", f"{user},{commit}")
        cls.committer_b = cls._user("pr_bver_committer_b", f"{user},{commit}")
        cls.reserve_type = cls.env.ref(
            "purchase_request_budget_todo.mail_activity_pr_reserve_budget"
        )

    @classmethod
    def _user(cls, login, groups):
        user = new_test_user(cls.env, login=login, groups=groups)
        user.write(
            {
                "operating_unit_ids": [Command.link(cls.ou.id)],
                "default_operating_unit_id": cls.ou.id,
            }
        )
        return user

    def _make_pr(self, **vals):
        vals = {
            "title": "Budget verifier test",
            "requested_by": self.requester.id,
            "operating_unit_id": self.ou.id,
            "assigned_to": self.verifier.id,
            "ignore_exception": True,
            "line_ids": [
                Command.create(
                    {"name": "Item", "product_qty": 1.0, "price_unit": 100.0}
                )
            ],
            **vals,
        }
        return self.env["purchase.request"].with_user(self.requester).create(vals)

    def _todos(self, pr):
        return pr.sudo().activity_ids.filtered(
            lambda a: a.activity_type_id == self.reserve_type
        )

    def _feedback(self, pr):
        return self.env["mail.message"].search(
            [
                ("model", "=", "purchase.request"),
                ("res_id", "=", pr.id),
                ("mail_activity_type_id", "=", self.reserve_type.id),
            ]
        )

    def _to_budget(self, **vals):
        pr = self._make_pr(budget_verifier_id=self.committer.id, **vals)
        pr.with_user(self.requester).button_to_verify()
        pr.with_user(self.verifier).button_to_approve()
        self.assertEqual(pr.state, "to_verify_budget")
        return pr

    def _reserve(self, pr, user):
        # Reserving needs a funded budget; only the state change matters here.
        pr.with_user(user).sudo().write({"state": "to_approve"})

    def test_broadcast_automation_disabled(self):
        automation = self.env.ref(
            "purchase_request_budget_todo.automation_pr_draft_to_verify"
        )
        self.assertFalse(automation.active)

    def test_verify_requires_budget_verifier(self):
        pr = self._make_pr()
        pr.with_user(self.requester).button_to_verify()
        with self.assertRaises(UserError):
            pr.with_user(self.verifier).button_to_approve()

    def test_non_committer_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_pr(budget_verifier_id=self.verifier.id)

    def test_verify_schedules_todo_for_budget_verifier(self):
        pr = self._to_budget()
        self.assertEqual(self._todos(pr).user_id, self.committer)

    def test_budget_verifier_reserves_todo_done(self):
        pr = self._to_budget()
        self._reserve(pr, self.committer)
        self.assertFalse(self._todos(pr))
        self.assertTrue(self._feedback(pr), "done activity posts a feedback message")

    def test_other_committer_reserves_todo_withdrawn(self):
        pr = self._to_budget()
        self._reserve(pr, self.committer_b)
        self.assertFalse(self._todos(pr))
        self.assertFalse(self._feedback(pr))

    def test_return_withdraws_todo(self):
        pr = self._to_budget()
        pr.with_user(self.committer).sudo()._action_do_return_to_draft("แก้ไขงบ")
        self.assertEqual(pr.state, "to_verify")
        self.assertFalse(self._todos(pr))
        self.assertFalse(self._feedback(pr))

    def test_recall_withdraws_todo(self):
        pr = self._to_budget()
        pr.with_user(self.verifier).sudo().action_recall_to_verify()
        self.assertEqual(pr.state, "to_verify")
        self.assertFalse(self._todos(pr))

    def test_reassign_moves_todo(self):
        pr = self._to_budget()
        pr.with_user(self.requester).budget_verifier_id = self.committer_b
        todo = self._todos(pr)
        self.assertEqual(len(todo), 1)
        self.assertEqual(todo.user_id, self.committer_b)

    def test_cannot_clear_while_to_verify_budget(self):
        pr = self._to_budget()
        with self.assertRaises(ValidationError):
            pr.with_user(self.requester).budget_verifier_id = False
