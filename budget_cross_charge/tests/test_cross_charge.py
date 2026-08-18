from datetime import date

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetCrossCharge(TransactionCase):
    """Cross-charge (ถัวจ่าย) reservations: flag gating, manual lines,
    header mirroring, and the reserved-edit window of the picker."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-XCHG",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.code_a = BA.create(
            {"code": "XCHG_A", "name": "Cross A", "budget_type": "expense"}
        )
        cls.code_b = BA.create(
            {"code": "XCHG_B", "name": "Cross B", "budget_type": "expense"}
        )
        Plan = env["account.analytic.plan"]
        fund_plan = Plan.search([("code", "=", "funds")], limit=1) or Plan.create(
            {"name": "Funds", "code": "funds"}
        )
        cls.fund = env["account.analytic.account"].create(
            {"name": "Cross Fund", "code": "XCHG_F", "plan_id": fund_plan.id}
        )

    # --- helpers ---

    def _dist(self):
        return {str(self.fund.id): 100.0}

    def _appropriate(self, account, amount):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account.id,
                            "balance": amount,
                            "fund_analytic_id": self.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _commitment(self, account_amounts, **kw):
        """Create a draft cross-charge commitment with one reserve line per
        (account, amount) pair, header mirroring the lines."""
        total = sum(amount for _account, amount in account_amounts)
        vals = {
            "date": date.today(),
            "title": "Cross-charge slip",
            "is_cross_charge": True,
            "account_id": account_amounts[0][0].id,
            "amount": total,
            "analytic_distribution": self._dist(),
            "account_fiscal_year_id": self.fy.id,
            "company_id": self.env.company.id,
            "currency_id": self.env.company.currency_id.id,
            "line_ids": [
                Command.create(
                    {
                        "move_type": "reserve",
                        "account_id": account.id,
                        "amount": amount,
                        "analytic_distribution": self._dist(),
                        "name": "Reserve",
                    }
                )
                for account, amount in account_amounts
            ],
        }
        vals.update(kw)
        return self.env["budget.commitment"].create(vals)

    # --- flag gating (constraint override) ---

    def test_multi_code_requires_flag(self):
        """>1 budget code needs every account flagged cross_chargeable."""
        with self.assertRaises(ValidationError):
            self._commitment([(self.code_a, 10_000), (self.code_b, 10_000)])
        (self.code_a | self.code_b).write({"cross_chargeable": True})
        commitment = self._commitment(
            [(self.code_a, 10_000), (self.code_b, 10_000)]
        )
        self.assertEqual(len(commitment.line_ids), 2)

    # --- manual-lines journey ---

    def test_manual_lines_reserve(self):
        """A cross-charge slip reserves from its typed lines; each line is
        availability-checked against its own account's pool."""
        (self.code_a | self.code_b).write({"cross_chargeable": True})
        self._appropriate(self.code_a, 50_000)
        self._appropriate(self.code_b, 50_000)
        c = self._commitment([(self.code_a, 30_000), (self.code_b, 20_000)])
        c.action_reserve()
        self.assertEqual(c.state, "reserved")
        self.assertEqual(c.total_reserved, 50_000)

    def test_cross_charge_without_lines_blocked(self):
        """No silent single-code fallback: a ถัวจ่าย slip with no lines cannot
        reserve (which code would the header synthesize?)."""
        c = self._commitment([(self.code_a, 10_000)])
        c.line_ids.unlink()  # draft staging: deletable
        with self.assertRaises(UserError):
            c.action_reserve()

    # --- header mirror (onchange) ---

    def test_onchange_seed_and_mirror(self):
        """Flipping to ถัวจ่าย seeds the grid from the header; the header then
        mirrors the lines (account = first line, amount = total)."""
        self.code_a.cross_chargeable = True
        self.code_b.cross_chargeable = True
        c = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Single-code slip",
                "account_id": self.code_a.id,
                "amount": 40_000,
                "analytic_distribution": self._dist(),
                "account_fiscal_year_id": self.fy.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        c.is_cross_charge = True
        c._onchange_is_cross_charge()
        self.assertEqual(len(c.line_ids), 1)
        seeded = c.line_ids
        self.assertEqual(seeded.move_type, "reserve")
        self.assertEqual(seeded.account_id, self.code_a)
        self.assertEqual(seeded.amount, 40_000)
        self.env["budget.commitment.line"].create(
            {
                "commitment_id": c.id,
                "move_type": "reserve",
                "account_id": self.code_b.id,
                "amount": 10_000,
            }
        )
        c._onchange_line_ids_sync_header()
        self.assertEqual(c.amount, 50_000)
        self.assertEqual(c.account_id, self.code_a)

    def test_line_without_distribution_stamped_from_header(self):
        """A grid/RPC line arriving without a distribution inherits the
        header's (one combination for the whole reservation)."""
        self.code_a.cross_chargeable = True
        c = self._commitment([(self.code_a, 10_000)])
        line = self.env["budget.commitment.line"].create(
            {
                "commitment_id": c.id,
                "move_type": "reserve",
                "account_id": self.code_a.id,
                "amount": 5_000,
            }
        )
        self.assertEqual(line.analytic_distribution, self._dist())

    # --- picker edit window ---

    def test_reserved_edit_replaces_and_rechecks(self):
        """Reserved with nothing obligated: the picker may replace the figures;
        the replacement is availability-checked (available >= 0)."""
        self.code_a.cross_chargeable = True
        self._appropriate(self.code_a, 100_000)
        c = self._commitment([(self.code_a, 60_000)])
        c.action_reserve()

        c.apply_reservation_selection(
            [{"account_id": self.code_a.id, "amount": 80_000}], self._dist()
        )
        self.assertEqual(c.total_reserved, 80_000)
        self.assertEqual(c.state, "reserved")
        # old line cancelled, not deleted (audit trail)
        cancelled = c.line_ids.filtered(lambda l: l.state == "cancel")
        self.assertEqual(cancelled.mapped("amount"), [60_000])

        # editing beyond the pool is blocked by the post-replacement re-check
        with self.assertRaises(UserError), self.env.cr.savepoint():
            c.apply_reservation_selection(
                [{"account_id": self.code_a.id, "amount": 120_000}], self._dist()
            )

    def test_edit_frozen_once_obligated(self):
        """Once something is obligated the figures are frozen — return or
        cancel instead of editing."""
        self.code_a.cross_chargeable = True
        self._appropriate(self.code_a, 100_000)
        c = self._commitment([(self.code_a, 60_000)])
        c.action_reserve()
        self.env["budget.commitment.line"].create(
            {
                "commitment_id": c.id,
                "move_type": "obligate",
                "account_id": self.code_a.id,
                "amount": 10_000,
                "analytic_distribution": self._dist(),
            }
        )
        with self.assertRaises(UserError):
            c.apply_reservation_selection(
                [{"account_id": self.code_a.id, "amount": 80_000}], self._dist()
            )
        with self.assertRaises(UserError):
            c.action_open_reservation_picker()

    def test_picker_context_carries_edit_selections(self):
        """Reopening the picker on a slip with reserve lines enters edit mode:
        the current figures ride in the context for the JS to seed."""
        self.code_a.cross_chargeable = True
        self._appropriate(self.code_a, 100_000)
        c = self._commitment([(self.code_a, 60_000)])
        c.action_reserve()
        action = c.action_open_reservation_picker()
        self.assertEqual(
            action["context"]["edit_selections"],
            [{"account_id": self.code_a.id, "amount": 60_000}],
        )
