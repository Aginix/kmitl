from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestVerifier(TransactionCase):
    """ผู้ยืนยันตรวจสอบ พ.1 (ADR-0011): required on submit, gets the to_verify
    Todo, which is done only when they press ตรวจสอบ and withdrawn otherwise;
    the verifier's ตีกลับ sends the requester (and creator) a Todo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ou = cls.env.ref("operating_unit.main_operating_unit")
        verify = "purchase_request_kmitl.group_purchase_request_verify"
        user = "purchase_request.group_purchase_request_user"
        cls.requester = cls._user("pr_ver_requester", user)
        # Filing a พ.1 for someone else needs All Documents (the plain user
        # rule only covers requested_by).
        cls.creator = cls._user(
            "pr_ver_creator",
            f"{user},purchase_request_kmitl.group_purchase_request_user_all",
        )
        cls.verifier = cls._user("pr_ver_verifier", f"{user},{verify}")
        cls.verifier_b = cls._user("pr_ver_verifier_b", f"{user},{verify}")
        cls.verify_type = cls.env.ref(
            "purchase_request_verifier.mail_activity_pr_verify"
        )
        cls.returned_type = cls.env.ref(
            "purchase_request_verifier.mail_activity_pr_returned"
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

    def _make_pr(self, creator=None, **vals):
        vals = {
            "title": "Verifier test",
            "requested_by": self.requester.id,
            "operating_unit_id": self.ou.id,
            "ignore_exception": True,
            "line_ids": [
                Command.create(
                    {"name": "Item", "product_qty": 1.0, "price_unit": 100.0}
                )
            ],
            **vals,
        }
        return (
            self.env["purchase.request"]
            .with_user(creator or self.requester)
            .create(vals)
        )

    def _todos(self, pr, act_type):
        return pr.sudo().activity_ids.filtered(lambda a: a.activity_type_id == act_type)

    def _submit(self, pr, user=None):
        # button_draft (ตีกลับ) clears ignore_exception; the rules aren't under test
        pr.ignore_exception = True
        pr.with_user(user or self.requester).button_to_verify()
        self.assertEqual(pr.state, "to_verify")

    def _verify(self, pr, user):
        # sudo keeps the presser as env.user but passes the
        # purchase_request_budget_verifier gate when it is installed too
        pr.with_user(user).sudo().button_to_approve()
        self.assertNotEqual(pr.state, "to_verify")

    def _return(self, pr, user=None):
        self.env["purchase.request.return.wizard"].with_user(
            user or self.verifier
        ).create({"request_id": pr.id, "reason": "แก้ไขรายการ"}).action_confirm()
        self.assertEqual(pr.state, "draft")

    def test_submit_requires_verifier(self):
        pr = self._make_pr()
        with self.assertRaises(UserError):
            pr.with_user(self.requester).button_to_verify()

    def test_superuser_submit_without_verifier(self):
        # Demo data and hooks submit in superuser mode (kmitl_demo)
        pr = self._make_pr().sudo()
        pr.button_to_verify()
        self.assertEqual(pr.state, "to_verify")

    def test_non_verifier_rejected(self):
        with self.assertRaises(ValidationError):
            self._make_pr(assigned_to=self.requester.id)

    def test_admin_without_duty_not_candidate(self):
        # base.group_erp_manager implies the Verifier group
        admin = self._user(
            "pr_ver_admin",
            "purchase_request.group_purchase_request_user,base.group_erp_manager",
        )
        self.assertNotIn(admin, self._make_pr()._get_verifier_candidates())

    def test_admin_with_duty_grant_is_candidate(self):
        role = self.env["res.groups"].create(
            {
                "name": "PR Verifier role",
                "implied_ids": [
                    Command.link(
                        self.env.ref(
                            "purchase_request_kmitl.group_purchase_request_verify"
                        ).id
                    )
                ],
            }
        )
        admin = self._user(
            "pr_ver_admin_duty",
            "purchase_request.group_purchase_request_user,base.group_erp_manager",
        )
        admin.groups_id = [Command.link(role.id)]
        self.assertIn(admin, self._make_pr()._get_verifier_candidates())

    def test_admin_role_also_granting_duty_is_candidate(self):
        # One role carrying both admin and the duty still grants the duty
        role = self.env["res.groups"].create(
            {
                "name": "Admin + PR Verifier role",
                "implied_ids": [
                    Command.link(self.env.ref("base.group_erp_manager").id),
                    Command.link(
                        self.env.ref(
                            "purchase_request_kmitl.group_purchase_request_verify"
                        ).id
                    ),
                ],
            }
        )
        admin = self._user(
            "pr_ver_admin_role", "purchase_request.group_purchase_request_user"
        )
        admin.groups_id = [Command.link(role.id)]
        self.assertIn(admin, self._make_pr()._get_verifier_candidates())

    def test_submit_schedules_todo_for_verifier(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        todo = self._todos(pr, self.verify_type)
        self.assertEqual(todo.user_id, self.verifier)

    def test_designated_verifier_verifies_todo_done(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        self._verify(pr, self.verifier)
        self.assertFalse(self._todos(pr, self.verify_type))
        done = self.env["mail.message"].search(
            [
                ("model", "=", "purchase.request"),
                ("res_id", "=", pr.id),
                ("mail_activity_type_id", "=", self.verify_type.id),
            ]
        )
        self.assertTrue(done, "done activity posts a feedback message")

    def test_other_verifier_verifies_todo_withdrawn(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        self._verify(pr, self.verifier_b)
        self.assertFalse(self._todos(pr, self.verify_type))
        self.assertFalse(
            self.env["mail.message"].search(
                [
                    ("model", "=", "purchase.request"),
                    ("res_id", "=", pr.id),
                    ("mail_activity_type_id", "=", self.verify_type.id),
                ]
            )
        )

    def test_requester_recall_withdraws_todo(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        pr.with_user(self.requester).button_draft()
        self.assertFalse(self._todos(pr, self.verify_type))
        self.assertFalse(self._todos(pr, self.returned_type))

    def test_cancel_withdraws_todo(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        pr.with_user(self.verifier)._action_do_cancel("ยกเลิก")
        self.assertEqual(pr.state, "cancelled")
        self.assertFalse(self._todos(pr, self.verify_type))

    def test_reassign_moves_todo(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        pr.with_user(self.requester).assigned_to = self.verifier_b
        todo = self._todos(pr, self.verify_type)
        self.assertEqual(len(todo), 1)
        self.assertEqual(todo.user_id, self.verifier_b)

    def test_cannot_clear_while_to_verify(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        with self.assertRaises(ValidationError):
            pr.with_user(self.requester).assigned_to = False

    def test_return_notifies_requester_and_creator(self):
        pr = self._make_pr(creator=self.creator, assigned_to=self.verifier.id)
        self._submit(pr, self.creator)
        self._return(pr)
        self.assertFalse(self._todos(pr, self.verify_type))
        returned = self._todos(pr, self.returned_type)
        self.assertEqual(returned.user_id, self.requester | self.creator)
        # The creator resubmits: theirs is done, the requester's withdrawn,
        # and the verifier is notified again.
        self._submit(pr, self.creator)
        self.assertFalse(self._todos(pr, self.returned_type))
        self.assertEqual(self._todos(pr, self.verify_type).user_id, self.verifier)

    def test_return_same_requester_and_creator_one_todo(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        self._return(pr)
        self.assertEqual(self._todos(pr, self.returned_type).user_id, self.requester)

    def test_cancel_after_return_withdraws_returned_todo(self):
        pr = self._make_pr(assigned_to=self.verifier.id)
        self._submit(pr)
        self._return(pr)
        pr.with_user(self.requester)._action_do_cancel("ไม่ต้องการแล้ว")
        self.assertFalse(self._todos(pr, self.returned_type))
