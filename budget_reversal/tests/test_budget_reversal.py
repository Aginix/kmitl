from datetime import timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestBudgetReversal(BudgetLedgerCommon):
    """กลับรายการ: a draft move offsetting a posted one (budget ADR-0020)."""

    def _reversal(self, original):
        action = original.action_reverse()
        return self.env["budget.move"].browse(action["res_id"])

    def _post(self, move):
        move.action_review()
        move.action_post()

    def test_reverse_creates_offsetting_draft(self):
        original = self._appropriate(100_000)
        self.assertTrue(original.can_reverse)
        reversal = self._reversal(original)
        self.assertEqual(reversal.state, "draft")
        self.assertEqual(reversal.reversed_move_id, original)
        self.assertEqual(reversal.move_type, "appropriation")
        self.assertEqual(reversal.appropriation_type, original.appropriation_type)
        self.assertEqual(reversal.account_fiscal_year_id, self.fy)
        self.assertTrue(self.fy.date_from <= reversal.date <= self.fy.date_to)
        self.assertIn(original.name, reversal.ref)
        self.assertEqual(reversal.line_ids.mapped("balance"), [-100_000])
        self.assertEqual(
            reversal.line_ids._reversal_key(), original.line_ids._reversal_key()
        )
        # a draft reversal moves nothing
        self.assertEqual(self._available(), 100_000)
        self.assertFalse(original.reversal_status)
        self.assertEqual(original.reversal_count, 1)

        self._post(reversal)
        self.assertEqual(self._available(), 0.0)
        self.assertEqual(original.state, "posted")
        self.assertEqual(original.reversal_status, "full")

    def test_partial_reversals_add_up_to_full(self):
        original = self._appropriate(100_000)
        first = self._reversal(original)
        first.line_ids.balance = -40_000
        self._post(first)
        self.assertEqual(original.reversal_status, "partial")
        self.assertEqual(self._available(), 60_000)

        second = self._reversal(original)
        second.line_ids.balance = -60_000
        self._post(second)
        self.assertEqual(original.reversal_status, "full")

    def test_post_blocked_beyond_available(self):
        original = self._appropriate(100_000)
        self._reserve(70_000)
        reversal = self._reversal(original)
        reversal.action_review()
        with self.assertRaises(UserError):
            reversal.action_post()
        # the free part may still be taken back
        reversal.line_ids.balance = -30_000
        reversal.action_post()
        self.assertEqual(reversal.state, "posted")
        self.assertEqual(self._available(), 0.0)

    def test_reset_original_blocked_while_reversal_live(self):
        original = self._appropriate(100_000)
        reversal = self._reversal(original)
        with self.assertRaises(UserError):
            original.button_draft()
        reversal.button_cancel()
        original.button_draft()
        self.assertEqual(original.state, "draft")

    def test_reversal_and_event_moves_not_reversible(self):
        original = self._appropriate(100_000)
        reversal = self._reversal(original)
        self._post(reversal)
        self.assertFalse(reversal.can_reverse)
        with self.assertRaises(UserError):
            reversal.action_reverse()

        event_move = self._reserve(1_000).ledger_line_ids.move_id
        self.assertTrue(event_move)
        self.assertFalse(any(m._is_reversible() for m in event_move))

    def test_reversal_stays_in_original_fiscal_year(self):
        reversal = self._reversal(self._appropriate(100_000))
        with self.assertRaises(ValidationError):
            reversal.date = self.fy.date_to + timedelta(days=1)
