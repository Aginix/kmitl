from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestBudgetCommitmentSplit(BudgetLedgerCommon):
    """Reservation Split (รายการจองงบประมาณ, ADR-0020)."""

    def setUp(self):
        super().setUp()
        (self.account | self.other).write({"cross_chargeable": True})
        self._appropriate(100_000)
        self._appropriate(100_000, account=self.other)

    def _split_draft(self, cap, other_amount):
        commitment = self._draft(cap)
        commitment.write(
            {
                "split_ids": [
                    Command.create(
                        {"account_id": self.other.id, "amount": other_amount}
                    )
                ]
            }
        )
        return commitment

    def _rows(self, commitment):
        return {(s.account_id, s.is_primary): s.amount for s in commitment.split_ids}

    def test_primary_row_is_the_remainder(self):
        commitment = self._split_draft(50_000, 20_000)
        self.assertEqual(
            self._rows(commitment),
            {(self.account, True): 30_000, (self.other, False): 20_000},
        )
        # A code already on a row is not offered again.
        self.assertNotIn(self.other, commitment.split_account_ids)
        self.assertIn(self.other, self._draft(10_000).split_account_ids)

    def test_reserve_posts_one_event_per_row_primary_first(self):
        commitment = self._split_draft(50_000, 20_000)
        commitment.action_reserve()
        events = commitment.line_ids.filtered(lambda line: line.state == "posted")
        self.assertEqual(
            [(e.account_id, e.amount) for e in events],
            [(self.account, 30_000), (self.other, 20_000)],
        )
        self.assertEqual(list(commitment._ledger_codes()), [self.account, self.other])
        other_row = commitment.split_ids.filtered(lambda s: not s.is_primary)
        self.assertEqual(other_row.total_reserved, 20_000)

    def test_primary_row_may_end_at_zero(self):
        commitment = self._split_draft(50_000, 50_000)
        self.assertFalse(commitment.split_warning)
        commitment.action_reserve()
        events = commitment.line_ids.filtered(lambda line: line.state == "posted")
        self.assertEqual(
            [(e.account_id, e.amount) for e in events], [(self.other, 50_000)]
        )
        self.assertEqual(commitment.total_reserved, 50_000)

    def test_over_cap_blocks_reserve(self):
        commitment = self._split_draft(50_000, 60_000)
        self.assertTrue(commitment.split_warning)
        with self.assertRaises(UserError):
            commitment.action_reserve()

    def test_unflagged_code_blocks_reserve(self):
        commitment = self._split_draft(50_000, 20_000)
        self.other.cross_chargeable = False
        with self.assertRaises(UserError):
            commitment.action_reserve()

    def test_recut_reserved_split(self):
        commitment = self._split_draft(50_000, 20_000)
        commitment.action_reserve()
        other_row = commitment.split_ids.filtered(lambda s: not s.is_primary)
        # Core keeps a reserved standalone slip read-only (กลับแบบร่าง instead);
        # an owner widening the window (the พ.1) reaches the same re-cut.
        commitment.sudo().write(
            {"split_ids": [Command.update(other_row.id, {"amount": 35_000})]}
        )
        posted = commitment.line_ids.filtered(lambda line: line.state == "posted")
        self.assertEqual(
            sorted((e.account_id.code, e.amount) for e in posted),
            sorted([(self.account.code, 15_000), (self.other.code, 35_000)]),
        )
        self.assertEqual(commitment.total_reserved, 50_000)
        self.assertEqual(self._available(account=self.other), 65_000)

    def test_slip_without_split_reserves_from_header(self):
        commitment = self._draft(10_000)
        commitment.action_reserve()
        self.assertFalse(commitment.split_ids)
        self.assertEqual(commitment.total_reserved, 10_000)
