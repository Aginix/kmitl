# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


def _sigs(dr, step):
    return dr.env["disbursement.request.signature"].search(
        [("request_id", "=", dr.id), ("step", "=", step)]
    )


@tagged("post_install", "-at_install")
class TestValidation(TwoApproverCommon):
    """The validate act stamps who acted and leaves one signature row; it
    never changes the request's state."""

    def test_validate_stamps_the_verifier_and_a_signature(self):
        dr = self._make_signed_dr()
        dr.with_user(self.officer).action_validate()
        self.assertEqual(dr.verifier_id, self.officer)
        self.assertTrue(dr.verify_date)
        self.assertEqual(dr.state, "signed")
        sig = _sigs(dr, "verify")
        self.assertEqual(len(sig), 1)
        self.assertEqual(sig.signed_by_id, self.officer)
        self.assertEqual(sig.signed_name, "Officer")

    def test_validating_twice_leaves_one_active_row(self):
        dr = self._make_signed_dr()
        dr.with_user(self.officer).action_validate()
        dr.with_user(self.officer).action_validate()
        self.assertEqual(len(_sigs(dr, "verify")), 1)

    def test_only_an_officer_may_validate(self):
        dr = self._make_signed_dr()
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            dr.with_user(self.finance).action_validate()
        self.assertFalse(dr.verifier_id)

    def test_cannot_validate_a_draft(self):
        dr = self.DR.create({"partner_type_id": self.partner.partner_type_id.id})
        with self.assertRaises(UserError):
            dr.with_user(self.officer).action_validate()

    def test_reset_to_draft_clears_the_stamp(self):
        dr = self._make_signed_dr()
        dr.with_user(self.officer).action_validate()
        dr.action_draft()
        self.assertFalse(dr.verifier_id)
        self.assertFalse(dr.verify_date)
        self.assertFalse(dr.signature_ids)
