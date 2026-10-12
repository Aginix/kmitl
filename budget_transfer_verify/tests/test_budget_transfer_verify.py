from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.budget_transfer_verify.models.budget_transfer import (
    CORRECT_ACTIVITY,
    VERIFY_ACTIVITY,
)


@tagged("post_install", "-at_install")
class TestBudgetTransferVerify(TransactionCase):
    """ยืนยัน → รอตรวจสอบ (number minted) → Buddy ยืนยันตรวจสอบ → submitted,
    or ส่งกลับแก้ไข → draft."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-BV",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.src = BA.create({"code": "BV_SRC", "name": "Src", "budget_type": "expense"})
        cls.dst = BA.create({"code": "BV_DST", "name": "Dst", "budget_type": "expense"})

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, code, plan_code, **extra):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            return AA.create({"name": name, "code": code, "plan_id": plan.id, **extra})

        cls.faculty = acc("Faculty", "BV_FAC", "departments")
        cls.dept = acc("Dept", "BV_DEPT", "departments", parent_id=cls.faculty.id)
        cls.source = acc("Source", "BV_SRCM", "sources")
        cls.activity = acc("Activity", "BV_ACT", "activities")
        cls.fund = acc("Fund", "BV_FUND", "funds")

        cls.requestor = new_test_user(
            env,
            login="bv_requestor",
            groups="base.group_user,budget.group_budget_user",
        )
        buddy_groups = "base.group_user,budget_buddy.group_budget_buddy"
        cls.buddy = new_test_user(env, login="bv_buddy", groups=buddy_groups)
        cls.buddy2 = new_test_user(env, login="bv_buddy2", groups=buddy_groups)
        cls.outsider = new_test_user(env, login="bv_outsider", groups=buddy_groups)
        Buddy = env["budget.buddy"]
        # Primary buddy on the unit itself, a backup via the parent faculty.
        Buddy.create({"user_id": cls.buddy.id, "department_analytic_id": cls.dept.id})
        Buddy.create(
            {"user_id": cls.buddy2.id, "department_analytic_id": cls.faculty.id}
        )

        move = env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": cls.fy.id,
                "department_analytic_id": cls.dept.id,
                "source_analytic_id": cls.source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": cls.src.id,
                            "balance": 100_000,
                            "activity_analytic_id": cls.activity.id,
                            "fund_analytic_id": cls.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()

    def _transfer(self, department=None, user=None):
        department = department or self.dept

        def line(account, direction):
            return Command.create(
                {
                    "transfer_direction": direction,
                    "account_id": account.id,
                    "amount": 1000,
                    "department_analytic_id": department.id,
                    "activity_analytic_id": self.activity.id,
                    "fund_analytic_id": self.fund.id,
                }
            )

        return (
            self.env["budget.transfer"]
            .with_user(user or self.requestor)
            .create(
                {
                    "date": date.today(),
                    "account_fiscal_year_id": self.fy.id,
                    "department_analytic_id": department.id,
                    "source_analytic_id": self.source.id,
                    "reason": "buddy verify test",
                    "line_ids": [line(self.src, "from"), line(self.dst, "to")],
                }
            )
        )

    def _activities(self, transfer, xmlid):
        return transfer.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref(xmlid)
        )

    def _submitted_for_verify(self):
        transfer = self._transfer()
        transfer.action_submit()
        return transfer

    # ------------------------------------------------------------------
    # ยืนยัน
    # ------------------------------------------------------------------
    def test_confirm_goes_to_verify_and_mints_number(self):
        transfer = self._submitted_for_verify()
        self.assertEqual(transfer.state, "to_verify")
        self.assertTrue(transfer.name.startswith("BTR/"))
        self.assertEqual(transfer.verifier_id, self.buddy, "the unit's own buddy")
        activity = self._activities(transfer, VERIFY_ACTIVITY)
        self.assertEqual(activity.user_id, self.buddy)

    def test_confirm_blocked_without_buddy(self):
        lonely = self.env["account.analytic.account"].create(
            {"name": "Lonely", "code": "BV_LONE", "plan_id": self.dept.plan_id.id}
        )
        transfer = self._transfer(department=lonely)
        with self.assertRaises(UserError):
            transfer.action_submit()
        self.assertEqual(transfer.state, "draft")

    def test_requester_buddy_is_not_assigned_to_self(self):
        transfer = self._transfer(user=self.buddy)
        transfer.with_user(self.buddy).action_submit()
        self.assertEqual(transfer.verifier_id, self.buddy2)

    def test_unverified_transfer_cannot_be_approved(self):
        transfer = self._submitted_for_verify()
        self.assertFalse(transfer.show_approve_button)

    # ------------------------------------------------------------------
    # ยืนยันตรวจสอบ
    # ------------------------------------------------------------------
    def test_backup_buddy_verifies(self):
        transfer = self._submitted_for_verify()
        transfer.with_user(self.buddy2).action_verify()
        self.assertEqual(transfer.state, "submitted")
        self.assertEqual(transfer.verifier_id, self.buddy2, "actual verifier stamped")
        self.assertTrue(transfer.verify_date)
        self.assertFalse(self._activities(transfer, VERIFY_ACTIVITY))

    def test_non_covering_user_cannot_verify(self):
        transfer = self._submitted_for_verify()
        with self.assertRaises(UserError):
            transfer.with_user(self.outsider).action_verify()
        with self.assertRaises(UserError):
            transfer.with_user(self.requestor).action_verify()

    def test_buddy_cannot_verify_own_transfer(self):
        transfer = self._transfer(user=self.buddy)
        transfer.with_user(self.buddy).action_submit()
        with self.assertRaises(UserError):
            transfer.with_user(self.buddy).action_verify()

    def test_only_buddy_edits_while_verifying(self):
        transfer = self._submitted_for_verify()
        self.assertTrue(transfer.with_user(self.buddy).can_edit)
        self.assertFalse(transfer.with_user(self.requestor).can_edit)
        self.assertFalse(transfer.with_user(self.outsider).can_edit)

    # ------------------------------------------------------------------
    # ส่งกลับแก้ไข / pull back / cancel
    # ------------------------------------------------------------------
    def test_return_for_correction(self):
        transfer = self._submitted_for_verify()
        number = transfer.name
        wizard = (
            self.env["budget.transfer.verify.return.wizard"]
            .with_user(self.buddy)
            .create({"transfer_id": transfer.id, "reason": "แก้กิจกรรม"})
        )
        wizard.action_confirm()
        self.assertEqual(transfer.state, "draft")
        self.assertEqual(transfer.name, number, "the BTR number is kept")
        self.assertFalse(self._activities(transfer, VERIFY_ACTIVITY))
        correct = self._activities(transfer, CORRECT_ACTIVITY)
        self.assertEqual(correct.user_id, self.requestor)
        # Re-confirming closes the requester's correction To-Do.
        transfer.action_submit()
        self.assertEqual(transfer.state, "to_verify")
        self.assertFalse(self._activities(transfer, CORRECT_ACTIVITY))

    def test_outsider_cannot_return(self):
        transfer = self._submitted_for_verify()
        with self.assertRaises(UserError):
            transfer.with_user(self.outsider)._action_verify_return("no")

    def test_requester_pulls_back(self):
        transfer = self._submitted_for_verify()
        self.assertTrue(transfer.show_reset_button)
        transfer.action_reset_to_draft()
        self.assertEqual(transfer.state, "draft")
        self.assertFalse(transfer.verifier_id)
        self.assertFalse(self._activities(transfer, VERIFY_ACTIVITY))

    def test_requester_cancels(self):
        transfer = self._submitted_for_verify()
        self.assertTrue(transfer.show_cancel_button)
        transfer.action_cancel()
        self.assertEqual(transfer.state, "cancelled")
        self.assertFalse(self._activities(transfer, VERIFY_ACTIVITY))
