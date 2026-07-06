# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestCashDeposit(ReceiptKmitlCommon):
    def test_pull_submit_post_flow(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        r2 = self._make_receipt()
        r2.action_confirm()

        deposit = self.env["kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id}
        )
        deposit.action_pull_pending_receipts()
        self.assertEqual(set(deposit.receipt_ids.ids), {r1.id, r2.id})
        self.assertEqual(deposit.amount_total, 10000.0)

        # Submit by department
        deposit.action_submit()
        self.assertEqual(deposit.state, "submitted")
        self.assertTrue(deposit.name.startswith("CD/01/"))

        # Post by central finance → each receipt gets its own move
        deposit.action_post()
        self.assertEqual(deposit.state, "posted")
        self.assertEqual(r1.state, "posted")
        self.assertEqual(r2.state, "posted")
        self.assertTrue(r1.move_id)
        self.assertTrue(r2.move_id)
        self.assertNotEqual(r1.move_id, r2.move_id)

    def test_pull_excludes_other_department(self):
        r_a = self._make_receipt(department=self.dept_a)
        r_a.action_confirm()
        r_b = self._make_receipt(department=self.dept_b)
        r_b.action_confirm()

        deposit = self.env["kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id}
        )
        deposit.action_pull_pending_receipts()
        self.assertEqual(deposit.receipt_ids.ids, [r_a.id])

    def test_pull_excludes_already_deposited(self):
        r1 = self._make_receipt()
        r1.action_confirm()
        d1 = self.env["kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id, "receipt_ids": [(6, 0, [r1.id])]}
        )
        d1.action_submit()

        r2 = self._make_receipt()
        r2.action_confirm()
        d2 = self.env["kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id}
        )
        d2.action_pull_pending_receipts()
        self.assertEqual(d2.receipt_ids.ids, [r2.id])
