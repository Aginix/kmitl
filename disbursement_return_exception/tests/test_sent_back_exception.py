# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestSentBackException(TwoApproverCommon):
    def test_send_back_marks_the_request_until_resubmitted(self):
        dr = self._make_signed_dr()
        marker = self.env.ref(
            "disbursement_return_exception.excep_disbursement_sent_back"
        )
        dr._action_return_for_edit("fix it")
        self.assertIn(marker, dr.exception_ids)
        self.assertEqual(dr.main_exception_id, marker)
        # Detection leaves the marker alone.
        dr.detect_exceptions()
        self.assertIn(marker, dr.exception_ids)
        with self._patch_circuit_entry():
            dr.action_resubmit_verification()
        self.assertNotIn(marker, dr.exception_ids)
