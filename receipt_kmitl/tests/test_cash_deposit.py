# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestCashDeposit(ReceiptKmitlCommon):
    def test_pull_and_confirm(self):
        r1 = self._make_receipt()
        r1.action_issue()
        r2 = self._make_receipt()
        r2.action_issue()

        deposit = self.env["receipt.kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id}
        )
        deposit.action_pull_today_receipts()
        self.assertEqual(set(deposit.receipt_ids.ids), {r1.id, r2.id})
        self.assertEqual(deposit.system_amount, 10000.0)

        # Confirm
        moves_before = self.env["account.move"].search_count([])
        deposit.action_confirm()
        moves_after = self.env["account.move"].search_count([])

        self.assertEqual(deposit.state, "confirmed")
        self.assertEqual(r1.state, "deposited")
        self.assertEqual(r2.state, "deposited")
        # No new JE created on deposit confirm (custodial transfer only)
        self.assertEqual(moves_after, moves_before)
        self.assertTrue(deposit.name.startswith("CD/01/"))

    def test_card_receipts_excluded(self):
        r_cash = self._make_receipt(payment_method="cash")
        r_cash.action_issue()
        r_card = self._make_receipt(payment_method="card")
        r_card.action_issue()

        deposit = self.env["receipt.kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id}
        )
        deposit.action_pull_today_receipts()
        self.assertEqual(deposit.receipt_ids.ids, [r_cash.id])

    def test_wrong_department_excluded(self):
        r_a = self._make_receipt(department=self.dept_a)
        r_a.action_issue()
        r_b = self._make_receipt(department=self.dept_b)
        r_b.action_issue()

        deposit = self.env["receipt.kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id}
        )
        deposit.action_pull_today_receipts()
        self.assertEqual(deposit.receipt_ids.ids, [r_a.id])
