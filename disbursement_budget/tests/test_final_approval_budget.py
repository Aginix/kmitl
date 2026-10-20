# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestFinalApprovalBudget(TwoApproverCommon):
    """The budget is consumed on the Rector-delegated approval only."""

    def test_budget_attempted_only_at_rector_step(self):
        """Finance approval must not touch the budget; the Rector step does."""
        dr = self._make_verified_dr()
        dr.with_user(self.finance).action_approve_finance()
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        # No commitment linked → the Rector step reaches the budget guard.
        with self.assertRaises(UserError):
            dr.with_user(self.rector).action_approve()
        self.assertEqual(dr.state, "verified")
