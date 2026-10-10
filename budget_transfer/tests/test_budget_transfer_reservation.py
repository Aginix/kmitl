from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestBudgetTransferReservation(BudgetLedgerCommon):
    """A transfer onto/off a reserved coordinate moves the reservation with it
    (budget ADR-0016, Q5/Q6)."""

    def _transfer(self, from_vals, to_vals):
        def line(vals, direction):
            return Command.create(
                dict(
                    {
                        "activity_analytic_id": self.activity.id,
                        "fund_analytic_id": self.fund.id,
                        "department_analytic_id": self.dept.id,
                    },
                    transfer_direction=direction,
                    **vals,
                )
            )

        return self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "reason": "ledger test",
                "line_ids": [line(from_vals, "from"), line(to_vals, "to")],
            }
        )

    def _post(self, transfer):
        # Straight to posting: the tag here names no real project, so the
        # project policy rules (other modules) are out of scope of these tests.
        transfer._post_transfer()

    def _own_pool(self, commitment):
        """Make ``commitment`` the owner of the project tag (the bridges'
        job), without depending on kmitl_project."""
        BudgetMoveLine = type(self.env["budget.move.line"])
        tag = self.tag

        def owner(line):
            if line.kmitl_project_analytic_id == tag:
                return commitment
            return line.env["budget.commitment"]

        return patch.object(BudgetMoveLine, "_get_pool_owner_commitment", owner)

    # ------------------------------------------------------------------
    # transfers (Q5/Q6)
    # ------------------------------------------------------------------
    def test_transfer_tops_reservation_up_and_releases(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            top_up = self._transfer(
                {"account_id": self.other.id, "amount": 30_000},
                {
                    "account_id": self.account.id,
                    "amount": 30_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
            )
            self._post(top_up)
            self.assertEqual(commitment.amount, 80_000)
            self.assertEqual(commitment.total_reserved, 80_000)
            self.assertEqual(self._available(tag=self.tag), 0.0)
            # the transfer's own FROM/TO stay balanced; the top-up rides along
            topup_line = top_up.move_id.line_ids.filtered("commitment_line_id")
            self.assertEqual(topup_line.move_type, "reserve")
            self.assertEqual(topup_line.balance, -30_000)
            self.assertEqual(top_up.amount, 30_000)

            release = self._transfer(
                {
                    "account_id": self.account.id,
                    "amount": 20_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
                {"account_id": self.other.id, "amount": 20_000},
            )
            self._post(release)
            self.assertEqual(commitment.amount, 60_000)
            self.assertEqual(commitment.total_reserved, 60_000)
            self.assertEqual(self._available(tag=self.tag), 0.0)

            # resetting the release gives the reservation its money back
            release.action_reset_to_draft()
            self.assertEqual(commitment.amount, 80_000)
            self.assertEqual(commitment.total_reserved, 80_000)

    def test_transfer_release_blocked_beyond_unobligated(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        commitment._post_budget_event("obligate", 40_000)
        with self._own_pool(commitment):
            release = self._transfer(
                {
                    "account_id": self.account.id,
                    "amount": 20_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
                {"account_id": self.other.id, "amount": 20_000},
            )
            # the release guard itself blocks, not only the check at ยืนยัน
            with self.assertRaises(UserError):
                self._post(release)

    def test_transfer_draws_free_money_before_releasing(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(100_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            for amount, cap in ((30_000, 50_000), (40_000, 30_000)):
                transfer = self._transfer(
                    {
                        "account_id": self.account.id,
                        "amount": amount,
                        "kmitl_project_analytic_id": self.tag.id,
                    },
                    {"account_id": self.other.id, "amount": amount},
                )
                self._post(transfer)
                self.assertEqual(commitment.amount, cap)
                self.assertEqual(commitment.total_reserved, cap)
        self.assertEqual(self._available(tag=self.tag), 0.0)

    def test_transfer_releases_whole_reservation(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            release = self._transfer(
                {
                    "account_id": self.account.id,
                    "amount": 50_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
                {"account_id": self.other.id, "amount": 50_000},
            )
            self._post(release)
        self.assertEqual(commitment.amount, 0.0)
        self.assertEqual(commitment.total_reserved, 0.0)
        self.assertEqual(commitment.state, "reserved")
        commitment.action_cancel()

    def test_transfer_reset_blocked_once_top_up_obligated(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            top_up = self._transfer(
                {"account_id": self.other.id, "amount": 30_000},
                {
                    "account_id": self.account.id,
                    "amount": 30_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
            )
            self._post(top_up)
            commitment._post_budget_event("obligate", 60_000)
            with self.assertRaises(UserError):
                top_up.action_reset_to_draft()

    def test_cancel_commitment_reverses_top_up_not_transfer(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            top_up = self._transfer(
                {"account_id": self.other.id, "amount": 30_000},
                {
                    "account_id": self.account.id,
                    "amount": 30_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
            )
            self._post(top_up)
        self.assertTrue(commitment._has_budget_event(top_up, "reserve"))
        commitment.action_cancel()
        self.assertFalse(commitment._budget_event_lines())
        self.assertEqual(top_up.move_id.state, "posted")
        self.assertEqual(top_up.state, "posted")
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": 0.0, "obligate": 0.0, "consume": 0.0},
        )
        self.assertEqual(self._available(tag=self.tag), 80_000)

    def _posted_commitment_lines(self, commitment):
        return self.env["budget.move.line"].search(
            [("commitment_id", "=", commitment.id), ("parent_state", "=", "posted")]
        )

    def test_reset_top_up_after_reservation_cancelled(self):
        """The cancelled reservation's reversal of the top-up goes with the
        top-up: no phantom −30,000 is left on the tag (Q6)."""
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            top_up = self._transfer(
                {"account_id": self.other.id, "amount": 30_000},
                {
                    "account_id": self.account.id,
                    "amount": 30_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
            )
            self._post(top_up)
            commitment.action_cancel()
            self.assertEqual(self._available(tag=self.tag), 80_000)
            top_up.action_reset_to_draft()
        self.assertEqual(top_up.move_id.state, "draft")
        self.assertFalse(top_up.move_id.line_ids.filtered("commitment_id"))
        self.assertFalse(self._posted_commitment_lines(commitment))
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": 0.0, "obligate": 0.0, "consume": 0.0},
        )
        self.assertEqual(commitment.amount, 50_000)
        self.assertEqual(self._available(tag=self.tag), 50_000)
        self.assertEqual(self._available(account=self.other), 100_000)

    def test_reset_release_after_reservation_cancelled(self):
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            release = self._transfer(
                {
                    "account_id": self.account.id,
                    "amount": 20_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
                {"account_id": self.other.id, "amount": 20_000},
            )
            self._post(release)
            self.assertEqual(commitment.amount, 30_000)
            commitment.action_cancel()
            self.assertEqual(self._available(tag=self.tag), 30_000)
            release.action_reset_to_draft()
        self.assertFalse(self._posted_commitment_lines(commitment))
        self.assertEqual(commitment.amount, 50_000)
        self.assertEqual(self._available(tag=self.tag), 50_000)
        self.assertEqual(self._available(account=self.other), 100_000)

    def test_transfer_move_with_top_up_is_locked(self):
        """The transfer's move can only leave posted through the transfer's
        own reset, which unwinds the top-up first."""
        self._appropriate(100_000, account=self.other)
        self._appropriate(50_000, tag=self.tag)
        commitment = self._reserve(50_000, tag=self.tag)
        with self._own_pool(commitment):
            top_up = self._transfer(
                {"account_id": self.other.id, "amount": 30_000},
                {
                    "account_id": self.account.id,
                    "amount": 30_000,
                    "kmitl_project_analytic_id": self.tag.id,
                },
            )
            self._post(top_up)
            with self.assertRaises(UserError):
                top_up.move_id.button_draft()
            self.assertEqual(commitment.total_reserved, 80_000)
            top_up.action_reset_to_draft()
        self.assertEqual(commitment.amount, 50_000)
        self.assertEqual(commitment.total_reserved, 50_000)
        self.assertEqual(self._available(tag=self.tag), 0.0)
