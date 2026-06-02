# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestSuspenseAllocation(ReceiptKmitlCommon):
    def _deposited_receipt(self):
        receipt = self._make_receipt()
        receipt.action_issue()
        deposit = self.env["receipt.kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id, "receipt_ids": [(6, 0, [receipt.id])]}
        )
        deposit.action_confirm()
        return receipt

    def test_allocation_posts_reclass_move(self):
        receipt = self._deposited_receipt()
        line = receipt.line_ids[0]

        allocation = self.env["receipt.kmitl.allocation"].create(
            {
                "journal_id": self.general_journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "receipt_line_id": line.id,
                            "income_account_id": self.income_tuition.id,
                        },
                    )
                ],
            }
        )

        allocation.action_post()
        self.assertEqual(allocation.state, "posted")
        self.assertTrue(allocation.move_id)
        self.assertEqual(allocation.move_id.state, "posted")

        # Dr Suspense / Cr Income
        debits = allocation.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credits = allocation.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debits.account_id, self.suspense_edu)
        self.assertEqual(credits.account_id, self.income_tuition)
        self.assertEqual(sum(debits.mapped("debit")), 5000.0)

        # Receipt fully allocated → state = reclassified
        self.assertEqual(receipt.state, "reclassified")
        self.assertTrue(line.allocation_line_id)

    def test_double_allocation_prevented(self):
        receipt = self._deposited_receipt()
        line = receipt.line_ids[0]

        a1 = self.env["receipt.kmitl.allocation"].create(
            {
                "journal_id": self.general_journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "receipt_line_id": line.id,
                            "income_account_id": self.income_tuition.id,
                        },
                    )
                ],
            }
        )
        a1.action_post()

        with self.assertRaises(Exception):
            a2 = self.env["receipt.kmitl.allocation"].create(
                {
                    "journal_id": self.general_journal.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "receipt_line_id": line.id,
                                "income_account_id": self.income_tuition.id,
                            },
                        )
                    ],
                }
            )
            a2.action_post()
