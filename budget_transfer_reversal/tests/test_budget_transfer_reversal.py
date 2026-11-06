from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon
from odoo.addons.budget_transfer.tests import test_budget_transfer_reservation


@tagged("post_install", "-at_install")
class TestBudgetTransferReversal(BudgetLedgerCommon):
    """กลับรายการ a posted budget transfer (budget ADR-0020)."""

    # Borrow the transfer helpers. Read through the module: a TestCase bound
    # in this module's namespace would be collected and its tests run again.
    _transfer = test_budget_transfer_reservation.TestBudgetTransferReservation._transfer
    _post = test_budget_transfer_reservation.TestBudgetTransferReservation._post
    _own_pool = test_budget_transfer_reservation.TestBudgetTransferReservation._own_pool

    def _posted_transfer(self, amount, **to_vals):
        transfer = self._transfer(
            {"account_id": self.other.id, "amount": amount},
            dict({"account_id": self.account.id, "amount": amount}, **to_vals),
        )
        transfer.write({"state": "submitted"})
        self._post(transfer)
        return transfer

    def _reversal(self, transfer):
        action = transfer.action_reverse()
        return self.env["budget.move"].browse(action["res_id"])

    def test_reverse_transfer_restores_both_pools(self):
        self._appropriate(100_000, account=self.other)
        transfer = self._posted_transfer(30_000)
        self.assertEqual(self._available(account=self.other), 70_000)

        reversal = self._reversal(transfer)
        self.assertFalse(reversal.is_transfer)
        self.assertEqual(reversal.move_type, "entry")
        self.assertEqual(reversal.reversed_move_id, transfer.move_id)
        self.assertEqual(sorted(reversal.line_ids.mapped("balance")), [-30_000, 30_000])
        self.assertTrue(all(not line.transfer_direction for line in reversal.line_ids))

        reversal.action_review()
        reversal.action_post()
        self.assertEqual(self._available(account=self.other), 100_000)
        self.assertEqual(self._available(), 0.0)
        self.assertEqual(transfer.state, "posted")
        self.assertEqual(transfer.reversal_status, "full")
        self.assertFalse(transfer.show_reset_posted_button)

    def test_reverse_top_up_needs_reservation_returned(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            transfer = self._posted_transfer(
                30_000, kmitl_project_analytic_id=self.tag.id
            )
            reversal = self._reversal(transfer)
            # the reservation top-up is not copied: only the pool lines are
            self.assertFalse(reversal.line_ids.filtered("commitment_id"))
            reversal.action_review()
            with self.assertRaises(UserError):
                reversal.action_post()

            self.env["budget.commitment.return.wizard"].create(
                {"commitment_id": commitment.id}
            ).action_confirm()
            reversal.action_post()
            self.assertEqual(self._available(account=self.other), 100_000)

    def test_reset_transfer_blocked_while_reversal_live(self):
        self._appropriate(100_000, account=self.other)
        transfer = self._posted_transfer(30_000)
        self._reversal(transfer)
        with self.assertRaises(UserError):
            transfer.action_reset_to_draft()
        self.assertEqual(transfer.state, "posted")
