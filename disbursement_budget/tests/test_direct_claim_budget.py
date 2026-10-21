# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestDirectClaimBudget(BudgetLedgerCommon):
    """A ตั้งเบิกตรง request (ADR-0005) has no reservation: its final approval
    posts a direct consumption (budget ADR-0019) on its own dimensions and
    budget code, gated by its approval chain rather than the Budget-Manager
    right; cancelling it gives the budget back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Direct Vendor",
                "bank_ids": [(0, 0, {"acc_number": "1234567890"})],
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Direct Service",
                "type": "service",
                "taxes_id": [(5, 0, 0)],
                "supplier_taxes_id": [(5, 0, 0)],
            }
        )
        cls.rector = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Direct Rector",
                    "login": "dc_rector",
                    "email": "dc_rector@example.com",
                    "groups_id": [
                        (
                            4,
                            cls.env.ref(
                                "disbursement.group_disbursement_rector_delegate"
                            ).id,
                        )
                    ],
                }
            )
        )

    def _claim(self, amount):
        dr = self.env["disbursement.request"].create(
            {
                "partner_type_id": self.partner.partner_type_id.id,
                "is_direct_claim": True,
                "memo_number": "อว 7201/1",
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.account.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "line",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "partner_id": self.partner.id,
                        },
                    )
                ],
            }
        )
        dr.analytic_distribution = self._distribution()
        self.env["ir.attachment"].create(
            {
                "name": "memo.pdf",
                "res_model": dr._name,
                "res_id": dr.id,
                "raw": b"%PDF-1.4",
            }
        )
        self.assertEqual(dr.amount_total, amount)
        return dr

    def _to_rector(self, dr):
        dr.action_submit()
        self.assertEqual(dr.state, "signed")
        dr.action_validate()
        dr.action_approve_finance()
        self.assertEqual(dr.approval_state, "pending_rector")

    def test_rector_consumes_directly_and_cancel_restores(self):
        self._appropriate(100_000)
        dr = self._claim(30_000)
        self._to_rector(dr)
        # The Rector delegate holds no budget right at all.
        dr.with_user(self.rector).action_approve()
        self.assertEqual(dr.state, "approved")
        move = dr.budget_direct_move_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.move_type, "consume")
        self.assertFalse(move.line_ids.commitment_id)
        self.assertEqual(dr.budget_consumed_amount, 30_000)
        self.assertEqual(self._available(), 70_000)
        # idempotent across a return to verification
        dr._action_approve_budget()
        self.assertEqual(self._available(), 70_000)

        dr.action_cancel()
        self.assertEqual(move.state, "cancel")
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        self.assertEqual(self._available(), 100_000)

    def test_submit_blocked_when_pool_short(self):
        self._appropriate(10_000)
        dr = self._claim(30_000)
        self.assertTrue(dr._direct_claim_budget_shortfall())
        dr.action_submit()
        # the blocking exception keeps it in draft
        self.assertEqual(dr.state, "draft")
        self.assertIn(
            self.env.ref(
                "disbursement_budget.excep_disbursement_direct_claim_budget_available"
            ),
            dr.exception_ids,
        )

    def test_approval_fails_when_pool_drained_meanwhile(self):
        self._appropriate(50_000)
        dr = self._claim(30_000)
        self._to_rector(dr)
        self._reserve(40_000)
        with self.assertRaises(UserError), self.env.cr.savepoint():
            dr.with_user(self.rector).action_approve()
        self.assertEqual(dr.state, "verified")
        self.assertFalse(dr.budget_direct_move_id)
