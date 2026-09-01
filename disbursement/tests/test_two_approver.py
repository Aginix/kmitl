# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

_DR = "disbursement.request"
_BUDGET_HOOK = "odoo.addons.disbursement.models.disbursement_request." \
    "DisbursementRequest._action_approve_budget"


@tagged("post_install", "-at_install")
class TestTwoApprover(TransactionCase):
    """The verified request needs two approvals in sequence: the Finance
    Division Director then the Rector-delegated approver. The budget is
    obligated/consumed only on the second (Rector) approval."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env[_DR]
        AAA = cls.env["account.analytic.account"]
        dep_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_departments")
        src_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_sources")
        fund_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_funds")
        act_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_activities")
        cls.dept = AAA.create({"name": "Dept", "plan_id": dep_plan.id})
        cls.source = AAA.create({"name": "Gov", "plan_id": src_plan.id})
        cls.fund = AAA.create({"name": "Fund", "plan_id": fund_plan.id})
        cls.activity = AAA.create({"name": "Act", "plan_id": act_plan.id})
        cls.partner = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Svc", "type": "service"}
        )
        users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.finance = users.create({
            "name": "Finance Director",
            "login": "ta_finance",
            "groups_id": [
                (4, cls.env.ref(
                    "disbursement.group_disbursement_finance_director").id)
            ],
        })
        cls.rector = users.create({
            "name": "Rector Delegate",
            "login": "ta_rector",
            "groups_id": [
                (4, cls.env.ref(
                    "disbursement.group_disbursement_rector_delegate").id)
            ],
        })
        cls.officer = users.create({
            "name": "Officer",
            "login": "ta_officer",
            "groups_id": [
                (4, cls.env.ref("disbursement.group_disbursement_officer").id)
            ],
        })
        cls.act_finance = cls.env.ref(
            "disbursement.mail_activity_dr_approve_finance")
        cls.act_rector = cls.env.ref(
            "disbursement.mail_activity_dr_approve_rector")
        cls.act_rejected = cls.env.ref("disbursement.mail_activity_dr_rejected")

    def _todos(self, dr, act_type):
        return dr.activity_ids.filtered(lambda a: a.activity_type_id == act_type)

    def _make_verified_dr(self):
        dr = self.DR.create({
            "line_ids": [(0, 0, {
                "product_id": self.product.id,
                "name": "line",
                "quantity": 1.0,
                "price_unit": 100.0,
                "partner_id": self.partner.id,
            })],
        })
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        dr.action_submit()
        dr.action_sign()
        dr.action_validate()
        self.assertEqual(dr.state, "verified")
        return dr

    def test_validate_opens_finance_step_with_todo(self):
        dr = self._make_verified_dr()
        self.assertEqual(dr.approval_state, "pending_finance")
        # The main status bar stays at 'verified'; the two-approver step is a
        # separate sub-status.
        self.assertEqual(dr.display_status, "verified")
        # A Todo was pushed to the Finance Director group. The fan-out reaches
        # every member, and security.xml seats root/admin in the group too, so
        # assert membership rather than a single assignee.
        finance_todos = self._todos(dr, self.act_finance)
        self.assertIn(self.finance, finance_todos.user_id)

    def test_full_two_step_approval(self):
        dr = self._make_verified_dr()
        # Step 1: Finance Director — no budget touched, hands to the Rector.
        dr.with_user(self.finance).action_approve_finance()
        self.assertEqual(dr.approval_state, "pending_rector")
        self.assertEqual(dr.state, "verified")
        self.assertEqual(dr.finance_approver_id, self.finance)
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        self.assertFalse(self._todos(dr, self.act_finance))
        self.assertIn(self.rector, self._todos(dr, self.act_rector).user_id)

        # Step 2: Rector-delegated approver — budget hook fires here only.
        with patch(_BUDGET_HOOK) as budget_hook:
            dr.with_user(self.rector).action_approve()
        budget_hook.assert_called_once()
        self.assertEqual(dr.state, "approved")
        self.assertEqual(dr.approval_state, "approved")
        self.assertEqual(dr.rector_approver_id, self.rector)
        self.assertFalse(self._todos(dr, self.act_rector))

    def test_budget_attempted_only_at_rector_step(self):
        """Finance approval must not touch the budget; the Rector step does."""
        dr = self._make_verified_dr()
        dr.with_user(self.finance).action_approve_finance()
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        # No commitment linked → the Rector step reaches the budget guard.
        with self.assertRaises(UserError):
            dr.with_user(self.rector).action_approve()

    def test_cannot_skip_finance_step(self):
        dr = self._make_verified_dr()
        with self.assertRaises(UserError):
            dr.with_user(self.rector).action_approve()

    def test_reject_notifies_requester_and_can_restart(self):
        dr = self._make_verified_dr()
        dr._action_reject("bad evidence")
        self.assertEqual(dr.approval_state, "rejected")
        self.assertEqual(dr.state, "verified")
        self.assertEqual(dr.approval_reject_reason, "bad evidence")
        self.assertFalse(self._todos(dr, self.act_finance))
        # Requester (creator) gets a rejected Todo.
        self.assertEqual(self._todos(dr, self.act_rejected).user_id, dr.user_id)

        dr.action_request_approval()
        self.assertEqual(dr.approval_state, "pending_finance")
        self.assertFalse(dr.approval_reject_reason)
        self.assertFalse(self._todos(dr, self.act_rejected))
        self.assertIn(self.finance, self._todos(dr, self.act_finance).user_id)

    def test_return_to_verification_resets_approval(self):
        dr = self._make_verified_dr()
        dr.with_user(self.finance).action_approve_finance()
        self.assertEqual(dr.approval_state, "pending_rector")
        dr._action_return_to_verification("recheck")
        self.assertEqual(dr.state, "signed")
        self.assertEqual(dr.approval_state, "none")
        self.assertFalse(self._todos(dr, self.act_finance))
        self.assertFalse(self._todos(dr, self.act_rector))

    def test_cancel_resets_approval(self):
        dr = self._make_verified_dr()
        dr.action_cancel()
        self.assertEqual(dr.state, "cancel")
        self.assertEqual(dr.approval_state, "none")
