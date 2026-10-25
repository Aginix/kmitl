# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestDirectClaimBudget(BudgetLedgerCommon):
    """A ตั้งเบิกตรง request (ADR-0005) has no reservation: its consume-budget act
    posts a direct consumption (budget ADR-0019) on its own dimensions and
    budget code, gated by the act's role rather than the Budget-Manager right;
    cancelling it gives the budget back."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Direct Vendor",
                "bank_ids": [(0, 0, {"acc_number": "1234567890"})],
            }
        )
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.env.company.id)],
            limit=1,
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
                "sign_date": "2026-10-01",
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.account.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.expense_account.id,
                            "name": "line",
                            "amount": amount,
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

    def _to_signed(self, dr):
        """Submit: a direct claim goes straight to ``signed``, and stays there
        whichever bridge routes it to a station."""
        with patch.object(type(dr), "_on_signed"):
            dr.action_submit()
        self.assertEqual(dr.state, "signed")

    def test_rector_consumes_directly_and_cancel_restores(self):
        self._appropriate(100_000)
        dr = self._claim(30_000)
        self._to_signed(dr)
        # The Rector delegate holds no budget right at all.
        dr.with_user(self.rector).action_consume_budget()
        move = dr.budget_direct_move_id
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.move_type, "consume")
        self.assertFalse(move.line_ids.commitment_id)
        self.assertEqual(dr.budget_consumed_amount, 30_000)
        self.assertEqual(self._available(), 70_000)
        # idempotent after a divert back
        dr._action_approve_budget()
        self.assertEqual(self._available(), 70_000)

        dr.action_cancel()
        self.assertEqual(move.state, "cancel")
        self.assertEqual(dr.budget_consumed_amount, 0.0)
        self.assertEqual(self._available(), 100_000)

    def test_direct_claim_may_draw_a_reservation(self):
        """A reservation is optional on a direct claim: linked, it is
        consumed through it like any request, not directly."""
        self._appropriate(100_000)
        commitment = self._reserve(50_000)
        dr = self._claim(30_000)
        dr.budget_commitment_id = commitment
        self._to_signed(dr)
        # Which path consumes is the point here, not the approver's rights
        # (the reservation path reads the commitment under the OU rules).
        dr.action_consume_budget()
        self.assertFalse(dr.budget_direct_move_id)
        self.assertTrue(commitment._has_budget_event(dr, "consume"))
        self.assertEqual(commitment.available_to_obligate, 20_000)

    def test_submit_blocked_when_pool_short(self):
        self._appropriate(10_000)
        dr = self._claim(30_000)
        self.assertTrue(dr._direct_claim_budget_shortfall())
        dr.action_submit()
        # the blocking exception keeps it in draft
        self.assertEqual(dr.state, "draft")
        self.assertIn(
            self.env.ref(
                "disbursement_direct_claim_budget.excep_disbursement_direct_claim_budget_available"
            ),
            dr.exception_ids,
        )

    def test_approval_fails_when_pool_drained_meanwhile(self):
        self._appropriate(50_000)
        dr = self._claim(30_000)
        self._to_signed(dr)
        self._reserve(40_000)
        with self.assertRaises(UserError), self.env.cr.savepoint():
            dr.with_user(self.rector).action_consume_budget()
        self.assertEqual(dr.state, "signed")
        self.assertFalse(dr.budget_direct_move_id)
