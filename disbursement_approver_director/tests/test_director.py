# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


def _sigs(dr, step):
    return dr.env["disbursement.request.signature"].search(
        [("request_id", "=", dr.id), ("step", "=", step)]
    )


@tagged("post_install", "-at_install")
class TestDirector(TwoApproverCommon):
    """The director act needs no prior validation and consumes no budget."""

    def test_director_acts_on_a_never_validated_request(self):
        dr = self._make_signed_dr()
        self.assertFalse(dr.verifier_id)
        self.assertTrue(dr.with_user(self.finance).can_approve_director)
        dr.with_user(self.finance).action_approve_finance()
        self.env.invalidate_all()
        self.assertFalse(dr.with_user(self.finance).can_approve_director)
        self.assertEqual(dr.finance_approver_id, self.finance)
        self.assertTrue(dr.finance_approve_date)
        self.assertEqual(len(_sigs(dr, "finance_approve")), 1)
        self.assertFalse(dr.budget_consumed_amount)

    def test_only_the_director_may_approve(self):
        dr = self._make_signed_dr()
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            dr.with_user(self.officer).action_approve_finance()
        self.assertFalse(dr.finance_approver_id)

    def test_cannot_approve_a_draft(self):
        dr = self.DR.create({"partner_type_id": self.partner.partner_type_id.id})
        with self.assertRaises(UserError):
            dr.with_user(self.finance).action_approve_finance()

    def test_reset_to_draft_clears_the_stamp(self):
        dr = self._make_signed_dr()
        dr.with_user(self.finance).action_approve_finance()
        dr.action_draft()
        self.assertFalse(dr.finance_approver_id)
        self.assertFalse(dr.finance_approve_date)
