# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestFinalApprovalBudget(TwoApproverCommon):
    """The budget is consumed by its own act, not by an approval."""

    def test_budget_consumed_only_by_its_own_act(self):
        dr = self._make_signed_dr()
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        # No commitment linked: the act reaches the budget guard.
        with self.assertRaises(UserError):
            dr.action_consume_budget()
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        # A request that draws no budget (a third-party deposit) is not
        # concerned: the act is not applicable and consumes nothing.
        dr.consumes_budget = False
        self.assertFalse(dr._disbursement_act_applicable("disbursement.consume_budget"))
        dr.action_consume_budget()
        self.assertEqual(dr.budget_consumed_amount, 0.0)
