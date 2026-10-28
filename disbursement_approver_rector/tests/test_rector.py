# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


def _sigs(dr, step):
    return dr.env["disbursement.request.signature"].search(
        [("request_id", "=", dr.id), ("step", "=", step)]
    )


@tagged("post_install", "-at_install")
class TestRector(TwoApproverCommon):
    """The rector-delegate act needs no director approval first (it replaces
    the old "cannot skip the finance step" rule) and consumes no budget."""

    def _make_signed_dr(self):
        dr = super()._make_signed_dr()
        # disbursement_approver_rector_budget (auto-installed next to
        # disbursement_budget) consumes on approval: test the act alone.
        if "consumes_budget" in dr._fields:
            dr.consumes_budget = False
        return dr

    def test_rector_acts_without_any_director_approval(self):
        dr = self._make_signed_dr()
        self.assertTrue(dr.with_user(self.rector).can_approve_rector)
        dr.with_user(self.rector).action_approve()
        self.env.invalidate_all()
        self.assertFalse(dr.with_user(self.rector).can_approve_rector)
        self.assertEqual(dr.rector_approver_id, self.rector)
        self.assertTrue(dr.rector_approve_date)
        self.assertEqual(len(_sigs(dr, "rector_approve")), 1)
        self.assertFalse(dr.budget_consumed_amount)

    def test_only_the_rector_delegate_may_approve(self):
        dr = self._make_signed_dr()
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            dr.with_user(self.finance).action_approve()
        self.assertFalse(dr.rector_approver_id)

    def test_cannot_approve_a_draft(self):
        dr = self.DR.create({"partner_type_id": self.partner.partner_type_id.id})
        with self.assertRaises(UserError):
            dr.with_user(self.rector).action_approve()

    def test_reset_to_draft_clears_the_stamp(self):
        dr = self._make_signed_dr()
        dr.with_user(self.rector).action_approve()
        dr.action_draft()
        self.assertFalse(dr.rector_approver_id)
        self.assertFalse(dr.rector_approve_date)
