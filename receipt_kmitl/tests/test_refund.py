# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestRefund(ReceiptKmitlCommon):
    def _deposited_receipt(self):
        receipt = self._make_receipt()
        receipt.action_issue()
        deposit = self.env["receipt.kmitl.cash.deposit"].create(
            {"department_id": self.dept_a.id, "receipt_ids": [(6, 0, [receipt.id])]}
        )
        deposit.action_confirm()
        return receipt

    def _reclassified_receipt(self):
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
        return receipt

    def test_refund_uses_suspense_when_not_reclassified(self):
        receipt = self._deposited_receipt()
        line = receipt.line_ids[0]

        refund = self.env["receipt.kmitl.refund"].create(
            {
                "receipt_id": receipt.id,
                "journal_id": self.cash_journal.id,
                "refund_method": "cash",
                "reason": "Mistake",
                "line_ids": [
                    (0, 0, {"receipt_line_id": line.id, "amount": line.amount})
                ],
            }
        )
        refund.action_submit()
        refund.action_post()

        self.assertEqual(refund.state, "posted")
        debits = refund.move_id.line_ids.filtered(lambda l: l.debit > 0)
        # Should hit suspense because line was not yet reclassified
        self.assertEqual(debits.account_id, self.suspense_edu)

    def test_refund_uses_income_when_reclassified(self):
        receipt = self._reclassified_receipt()
        line = receipt.line_ids[0]

        refund = self.env["receipt.kmitl.refund"].create(
            {
                "receipt_id": receipt.id,
                "journal_id": self.cash_journal.id,
                "refund_method": "cash",
                "reason": "Mistake",
                "line_ids": [
                    (0, 0, {"receipt_line_id": line.id, "amount": line.amount})
                ],
            }
        )
        refund.action_submit()
        refund.action_post()

        debits = refund.move_id.line_ids.filtered(lambda l: l.debit > 0)
        # Should hit income because line was reclassified
        self.assertEqual(debits.account_id, self.income_tuition)

    def test_partial_refund(self):
        receipt = self._deposited_receipt()
        line = receipt.line_ids[0]

        refund = self.env["receipt.kmitl.refund"].create(
            {
                "receipt_id": receipt.id,
                "journal_id": self.cash_journal.id,
                "refund_method": "cash",
                "reason": "Partial",
                "line_ids": [(0, 0, {"receipt_line_id": line.id, "amount": 2000.0})],
            }
        )
        refund.action_submit()
        refund.action_post()
        self.assertEqual(refund.amount_total, 2000.0)
