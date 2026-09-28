# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountMoveWorkflow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        accounts = cls.env["account.account"].search(
            [("company_id", "=", cls.company.id)], limit=2
        )
        cls.account_a, cls.account_b = accounts[0], accounts[1]

        group_user = cls.env.ref("accounting_kmitl.group_accounting_kmitl_user")
        group_manager = cls.env.ref(
            "accounting_kmitl.group_accounting_kmitl_manager"
        )
        account_manager = cls.env.ref("account.group_account_manager")
        cls.maker = cls.env["res.users"].create(
            {
                "name": "Maker",
                "login": "kmitl_maker",
                "groups_id": [Command.set([group_user.id, account_manager.id])],
            }
        )
        cls.approver = cls.env["res.users"].create(
            {
                "name": "Approver",
                "login": "kmitl_approver",
                "groups_id": [Command.set([group_manager.id])],
            }
        )

    def _new_entry(self):
        # Created as the maker so create_uid == maker (submit is creator-only).
        return self.env["account.move"].with_user(self.maker).create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_a.id,
                            "debit": 100.0,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.account_b.id,
                            "debit": 0.0,
                            "credit": 100.0,
                        }
                    ),
                ],
            }
        )

    def test_submit_sets_to_approve(self):
        move = self._new_entry().with_user(self.maker)
        move.action_submit()
        self.assertEqual(move.state, "submitted")
        self.assertEqual(move.workflow_state, "to_approve")
        self.assertEqual(move.submitted_by, self.maker)
        self.assertEqual(move.display_state, "to_approve")
        self.assertTrue(move.hide_post_button)

    def test_approve_posts_entry(self):
        move = self._new_entry()
        move.with_user(self.maker).action_submit()
        move.with_user(self.approver).action_approve()
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.workflow_state, "approved")
        self.assertEqual(move.approved_by, self.approver)
        self.assertEqual(move.display_state, "posted")

    def test_only_creator_can_submit(self):
        move = self._new_entry()  # created by the maker
        # A different non-admin user cannot submit someone else's entry.
        with self.assertRaises(UserError):
            move.with_user(self.approver).action_submit()
        # The creator can.
        move.with_user(self.maker).action_submit()
        self.assertEqual(move.workflow_state, "to_approve")

    def test_maker_can_approve_own_entry(self):
        """The maker and approver may be the same person."""
        move = self._new_entry()
        move.with_user(self.maker).action_submit()
        move.with_user(self.maker).action_approve()
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.approved_by, self.maker)

    def test_reject_returns_to_draft(self):
        move = self._new_entry()
        move.with_user(self.maker).action_submit()
        move.with_user(self.approver).action_reject("missing document")
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.workflow_state, "rejected")
        self.assertEqual(move.display_state, "draft")

    def test_reject_notifies_maker_and_clears_on_resubmit(self):
        rejected_type = self.env.ref(
            "accounting_kmitl_workflow.mail_activity_move_rejected"
        )
        move = self._new_entry()
        move.with_user(self.maker).action_submit()
        move.with_user(self.approver).action_reject("missing document")
        activity = move.activity_ids.filtered(
            lambda a: a.activity_type_id == rejected_type
        )
        self.assertTrue(activity, "a Todo should be pushed to the maker")
        self.assertEqual(activity.user_id, self.maker)
        # Resubmitting the fixed entry clears the Todo.
        move.with_user(self.maker).action_submit()
        self.assertFalse(
            move.activity_ids.filtered(
                lambda a: a.activity_type_id == rejected_type
            )
        )

    def test_submit_notifies_approvers_and_clears_on_approve(self):
        to_approve_type = self.env.ref(
            "accounting_kmitl_workflow.mail_activity_move_to_approve"
        )
        move = self._new_entry()
        move.with_user(self.maker).action_submit()
        activities = move.activity_ids.filtered(
            lambda a: a.activity_type_id == to_approve_type
        )
        self.assertTrue(activities, "approvers should get a Todo on submit")
        self.assertIn(self.approver, activities.mapped("user_id"))
        # Approving clears the approvers' Todo.
        move.with_user(self.approver).action_approve()
        self.assertFalse(
            move.activity_ids.filtered(
                lambda a: a.activity_type_id == to_approve_type
            )
        )

    def test_submitter_who_is_approver_gets_own_todo(self):
        """An approver who submits their own entry still receives the
        'to approve' Todo so it surfaces in their Todo inbox."""
        to_approve_type = self.env.ref(
            "accounting_kmitl_workflow.mail_activity_move_to_approve"
        )
        maker_approver = self.env["res.users"].create(
            {
                "name": "Maker Approver",
                "login": "kmitl_maker_approver",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref(
                                "accounting_kmitl.group_accounting_kmitl_user"
                            ).id,
                            self.env.ref(
                                "accounting_kmitl.group_accounting_kmitl_manager"
                            ).id,
                            self.env.ref("account.group_account_manager").id,
                        ]
                    )
                ],
            }
        )
        move = self.env["account.move"].with_user(maker_approver).create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_a.id,
                            "debit": 100.0,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.account_b.id,
                            "debit": 0.0,
                            "credit": 100.0,
                        }
                    ),
                ],
            }
        )
        move.with_user(maker_approver).action_submit()
        activities = move.activity_ids.filtered(
            lambda a: a.activity_type_id == to_approve_type
        )
        self.assertIn(maker_approver, activities.mapped("user_id"))

    def test_recall_returns_to_draft(self):
        move = self._new_entry()
        move.with_user(self.maker).action_submit()
        move.with_user(self.maker).action_draft()
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.workflow_state, "none")

    def test_recall_blocked_for_other_user(self):
        move = self._new_entry()
        move.with_user(self.maker).action_submit()
        other = self.env["res.users"].create(
            {
                "name": "Other",
                "login": "kmitl_other",
                "groups_id": [
                    Command.set(
                        [
                            self.env.ref(
                                "accounting_kmitl.group_accounting_kmitl_user"
                            ).id,
                            self.env.ref("account.group_account_manager").id,
                        ]
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            move.with_user(other).action_draft()

    def test_batch_approve_posts_all(self):
        move1 = self._new_entry()
        move2 = self._new_entry()
        (move1 | move2).with_user(self.maker).action_submit()
        result = (move1 | move2).with_user(self.approver).action_approve_batch()
        self.assertEqual(move1.state, "posted")
        self.assertEqual(move2.state, "posted")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")

    def test_batch_approve_skips_non_candidates(self):
        submitted = self._new_entry()
        submitted.with_user(self.maker).action_submit()
        draft = self._new_entry()
        (submitted | draft).with_user(self.approver).action_approve_batch()
        self.assertEqual(submitted.state, "posted")
        self.assertEqual(draft.state, "draft")
        self.assertEqual(draft.workflow_state, "none")

    def test_system_move_bypasses_workflow(self):
        """A move posted programmatically never enters the workflow."""
        move = self._new_entry()
        move._post(soft=False)
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.workflow_state, "none")
        self.assertEqual(move.display_state, "posted")

    def test_kmitl_voucher_lines_debit_first(self):
        """_kmitl_voucher_lines() puts every debit row before every credit
        row, even when the entry was keyed credit-first, and keeps each
        side in the order the lines were keyed in."""
        move = self.env["account.move"].with_user(self.maker).create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_b.id,
                            "debit": 0.0,
                            "credit": 1000.0,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.account_a.id,
                            "debit": 600.0,
                            "credit": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.account_a.id,
                            "debit": 400.0,
                            "credit": 0.0,
                        }
                    ),
                ],
            }
        )
        lines = move._kmitl_voucher_lines()
        self.assertEqual(lines.mapped("debit"), [600.0, 400.0, 0.0])
        self.assertEqual(lines.mapped("credit"), [0.0, 0.0, 1000.0])
