# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import tagged

from odoo.addons.disbursement.tests.test_two_approver import TwoApproverCommon


@tagged("post_install", "-at_install")
class TestCheque(TwoApproverCommon):
    """A cheque payee needs no bank account."""

    def _draft(self):
        dr = self.DR.create(
            {
                "partner_type_id": self.partner.partner_type_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.expense_account.id,
                            "name": "line",
                            "amount": 100.0,
                            "partner_id": self.partner.id,
                        },
                    )
                ],
            }
        )
        dr.analytic_distribution = {
            str(self.dept.id): 100,
            str(self.source.id): 100,
            str(self.fund.id): 100,
            str(self.activity.id): 100,
        }
        return dr

    def test_cheque_payee_needs_no_bank(self):
        self.partner.bank_ids.unlink()
        dr = self._draft()
        dr.line_ids.payment_method = "cheque"
        dr.action_submit()
        self.assertEqual(dr.state, "submitted")
        self.assertNotIn(
            self.env.ref("disbursement.excep_disbursement_line_partner_bank"),
            dr.exception_ids,
        )

    def test_switching_to_cheque_clears_bank(self):
        dr = self._draft()
        self.assertTrue(dr.line_ids.partner_bank_id)
        dr.line_ids.payment_method = "cheque"
        self.assertFalse(dr.line_ids.partner_bank_id)
        dr.line_ids.payment_method = "transfer"
        self.assertTrue(dr.line_ids.partner_bank_id)
