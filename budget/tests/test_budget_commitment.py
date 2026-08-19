from datetime import date

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetCommitment(TransactionCase):
    """Test budget.commitment ledger-style multi-line operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # Fiscal year covering today
        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-TEST",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": env.company.id,
                }
            )

        # Analytic plans (from account_analytic_kmitl data)
        Plan = env["account.analytic.plan"]
        cls.plan_activities = Plan.search([("code", "=", "activities")], limit=1)
        cls.plan_departments = Plan.search([("code", "=", "departments")], limit=1)
        cls.plan_funds = Plan.search([("code", "=", "funds")], limit=1)
        cls.plan_sources = Plan.search([("code", "=", "sources")], limit=1)

        if not cls.plan_activities:
            cls.plan_activities = Plan.create(
                {"name": "Activities", "code": "activities"}
            )
        if not cls.plan_departments:
            cls.plan_departments = Plan.create(
                {"name": "Departments", "code": "departments"}
            )
        if not cls.plan_funds:
            cls.plan_funds = Plan.create({"name": "Funds", "code": "funds"})
        if not cls.plan_sources:
            cls.plan_sources = Plan.create({"name": "Sources", "code": "sources"})

        # Analytic accounts
        AA = env["account.analytic.account"]
        cls.activity = AA.create(
            {
                "name": "Test Activity",
                "code": "TEST_ACT",
                "plan_id": cls.plan_activities.id,
            }
        )
        cls.department = AA.create(
            {
                "name": "Test Department",
                "code": "TEST_DEPT",
                "plan_id": cls.plan_departments.id,
            }
        )
        cls.fund = AA.create(
            {
                "name": "Test Fund",
                "code": "TEST_FUND",
                "plan_id": cls.plan_funds.id,
            }
        )
        cls.source = AA.create(
            {
                "name": "Test Source",
                "code": "TEST_SRC",
                "plan_id": cls.plan_sources.id,
            }
        )

        # Budget accounts (two different accounts, same dimensions)
        BA = env["budget.account"]
        cls.account_1 = BA.search(
            [("budgetable", "=", True), ("budget_type", "=", "expense")], limit=1
        )
        if not cls.account_1:
            cls.account_1 = BA.create(
                {
                    "code": "TEST001",
                    "name": "Test Account 1",
                    "budget_type": "expense",
                    "budgetable": True,
                }
            )
        cls.account_2 = BA.search(
            [
                ("budgetable", "=", True),
                ("budget_type", "=", "expense"),
                ("id", "!=", cls.account_1.id),
            ],
            limit=1,
        )
        if not cls.account_2:
            cls.account_2 = BA.create(
                {
                    "code": "TEST002",
                    "name": "Test Account 2",
                    "budget_type": "expense",
                    "budgetable": True,
                }
            )

    # --- Helpers ---

    def _header_analytic(self):
        """Build header analytic_distribution (department + source + activity + fund)."""
        return {
            str(self.department.id): 100.0,
            str(self.source.id): 100.0,
            str(self.activity.id): 100.0,
            str(self.fund.id): 100.0,
        }

    def _line_analytic(self):
        """Build line analytic_distribution (activity + fund)."""
        return {
            str(self.activity.id): 100.0,
            str(self.fund.id): 100.0,
        }

    def _create_commitment(self, amount, account_id=None, **kw):
        """Create a commitment in draft state with a single reserve line."""
        vals = {
            "date": date.today(),
            "title": "Test commitment",
            "account_id": (account_id or self.account_1).id,
            "amount": amount,
            "analytic_distribution": self._header_analytic(),
            "account_fiscal_year_id": self.fiscal_year.id,
            "company_id": self.env.company.id,
            "currency_id": self.env.company.currency_id.id,
            "line_ids": [
                Command.create(
                    {
                        "move_type": "reserve",
                        "account_id": (account_id or self.account_1).id,
                        "analytic_distribution": self._line_analytic(),
                        "amount": amount,
                        "name": "Reserve",
                    }
                )
            ],
        }
        vals.update(kw)
        return self.env["budget.commitment"].create(vals)

    def _add_line(self, commitment, move_type, amount, account_id=None, **kw):
        """Add a ledger line to a commitment."""
        vals = {
            "commitment_id": commitment.id,
            "move_type": move_type,
            "account_id": (account_id or commitment.account_id).id,
            "analytic_distribution": self._line_analytic(),
            "amount": amount,
            "name": move_type,
        }
        vals.update(kw)
        return self.env["budget.commitment.line"].create(vals)

    # ====================================================================
    # 1. Basic lifecycle: draft -> reserved -> partial -> done / cancel
    # ====================================================================

    def test_01_basic_reserve(self):
        """Draft commitment with a reserve line can be reserved."""
        c = self._create_commitment(100_000)
        self.assertEqual(c.state, "draft")
        c.action_reserve()
        self.assertEqual(c.state, "reserved")
        self.assertEqual(c.total_reserved, 100_000)

    def test_02_reserve_without_lines_creates_from_header(self):
        """Form-first journey: reserving with no lines synthesizes the single
        reserve line from the header — code, dimensions and money are entered
        once, on the form, with no picker dialog."""
        c = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Test commitment",
                "account_id": self.account_1.id,
                "amount": 50_000,
                "analytic_distribution": self._header_analytic(),
                "account_fiscal_year_id": self.fiscal_year.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        c.action_reserve()
        self.assertEqual(c.state, "reserved")
        line = c.line_ids
        self.assertEqual(len(line), 1)
        self.assertEqual(line.move_type, "reserve")
        self.assertEqual(line.account_id, self.account_1)
        self.assertEqual(line.amount, 50_000)
        self.assertEqual(line.analytic_distribution, self._header_analytic())
        self.assertEqual(c.total_reserved, 50_000)

    def test_02b_reserve_requires_positive_amount(self):
        """A zero วงเงินอนุมัติ is allowed while draft (staging) but cannot be
        reserved — pressing จองงบประมาณ requires a positive amount."""
        c = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Zero-cap draft",
                "account_id": self.account_1.id,
                "amount": 0,
                "analytic_distribution": self._header_analytic(),
                "account_fiscal_year_id": self.fiscal_year.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.assertEqual(c.state, "draft")
        with self.assertRaises(UserError):
            c.action_reserve()

    def test_03_obligate_moves_to_partial(self):
        """Adding an obligate line transitions header to partial."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 50_000)
        self.assertEqual(c.state, "partial")
        self.assertEqual(c.total_obligated, 50_000)
        self.assertEqual(c.available_to_obligate, 50_000)

    def test_04_consume_moves_to_partial(self):
        """Adding a consume line transitions header to partial."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 100_000)
        self._add_line(c, "consume", 30_000)
        self.assertEqual(c.state, "partial")
        self.assertEqual(c.total_consumed, 30_000)
        self.assertEqual(c.available_to_consume, 70_000)

    def test_05_action_done(self):
        """A reserved commitment can be closed."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        c.action_done()
        self.assertEqual(c.state, "done")

    def test_06_cancel_and_reset(self):
        """Cancel then reset to draft."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        c.action_cancel()
        self.assertEqual(c.state, "cancel")
        # All posted lines should be cancelled
        self.assertTrue(
            all(l.state == "cancel" for l in c.line_ids)
        )
        c.action_reset_to_draft()
        self.assertEqual(c.state, "draft")

    # ====================================================================
    # 2. Cascade constraints: reserved <= cap, obligated <= reserved, consumed <= obligated
    # ====================================================================

    def test_10_reserve_exceeds_cap(self):
        """Total reserved cannot exceed the header cap amount."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        with self.assertRaises(ValidationError):
            self._add_line(c, "reserve", 1)

    def test_11_obligate_exceeds_reserved(self):
        """Total obligated cannot exceed total reserved."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        with self.assertRaises(ValidationError):
            self._add_line(c, "obligate", 100_001)

    def test_12_consume_exceeds_obligated(self):
        """Total consumed cannot exceed total obligated."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 50_000)
        with self.assertRaises(ValidationError):
            self._add_line(c, "consume", 50_001)

    # ====================================================================
    # 3. Immutability of posted lines
    # ====================================================================

    def test_20_posted_line_cannot_be_edited(self):
        """Protected fields on a posted line cannot be edited."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        line = c.line_ids[0]
        self.assertEqual(line.state, "posted")
        with self.assertRaises(UserError):
            line.write({"amount": 999})

    def test_21_posted_line_cannot_be_deleted(self):
        """Posted lines cannot be deleted."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        with self.assertRaises(UserError):
            c.line_ids[0].unlink()

    def test_22_cancelled_line_can_be_deleted(self):
        """Cancelled lines can be deleted."""
        c = self._create_commitment(100_000)
        # Line created in posted state; cancel it first
        line = c.line_ids[0]
        line.action_cancel()
        self.assertEqual(line.state, "cancel")
        line.unlink()
        self.assertFalse(c.line_ids)

    # ====================================================================
    # 4. Consume auto-creates budget.move
    # ====================================================================

    def test_30_consume_creates_budget_move(self):
        """A consume line auto-creates a posted budget.move."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 100_000)
        consume_line = self._add_line(c, "consume", 40_000)
        self.assertTrue(consume_line.budget_move_id)
        self.assertEqual(consume_line.budget_move_id.state, "posted")
        self.assertEqual(consume_line.budget_move_id.move_type, "consume")

    def test_31_cancel_consume_cascades_to_move(self):
        """Cancelling a consume line cascades to its budget.move."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 100_000)
        consume_line = self._add_line(c, "consume", 40_000)
        bm = consume_line.budget_move_id
        consume_line.action_cancel()
        self.assertEqual(bm.state, "cancel")

    # ====================================================================
    # 5. Multiple budget accounts, same dimensions
    # ====================================================================

    def test_40_multi_account_same_dimensions(self):
        """Reserve two different budget accounts in separate commitments, same analytics."""
        c1 = self._create_commitment(80_000, account_id=self.account_1)
        c1.action_reserve()

        c2 = self._create_commitment(60_000, account_id=self.account_2)
        c2.action_reserve()

        self.assertEqual(c1.total_reserved, 80_000)
        self.assertEqual(c2.total_reserved, 60_000)
        self.assertEqual(c1.account_id, self.account_1)
        self.assertEqual(c2.account_id, self.account_2)

    def test_41_multi_account_independent_constraints(self):
        """Constraints on one commitment don't affect another."""
        c1 = self._create_commitment(50_000, account_id=self.account_1)
        c1.action_reserve()
        self._add_line(c1, "obligate", 50_000, account_id=self.account_1)
        self._add_line(c1, "consume", 50_000, account_id=self.account_1)

        c2 = self._create_commitment(70_000, account_id=self.account_2)
        c2.action_reserve()
        # c2 is still fully available
        self.assertEqual(c2.available_to_obligate, 70_000)

    # ====================================================================
    # 6. Reversal lines (negative amounts)
    # ====================================================================

    def test_50_obligate_reversal(self):
        """Negative obligate line (return) increases available_to_obligate."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 60_000)
        self.assertEqual(c.available_to_obligate, 40_000)
        # Return 20k of the obligation
        self._add_line(c, "obligate", -20_000)
        self.assertEqual(c.total_obligated, 40_000)
        self.assertEqual(c.available_to_obligate, 60_000)

    def test_51_consume_reversal(self):
        """Negative consume line (refund) increases available_to_consume."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 100_000)
        self._add_line(c, "consume", 60_000)
        self.assertEqual(c.available_to_consume, 40_000)
        # Refund 10k
        self._add_line(c, "consume", -10_000)
        self.assertEqual(c.total_consumed, 50_000)
        self.assertEqual(c.available_to_consume, 50_000)

    # ====================================================================
    # 7. Computed balance formulas
    # ====================================================================

    def test_60_balance_formulas(self):
        """Verify all computed balance formulas after mixed operations."""
        c = self._create_commitment(200_000)
        c.action_reserve()
        self._add_line(c, "obligate", 120_000)
        self._add_line(c, "consume", 80_000)

        self.assertEqual(c.total_reserved, 200_000)
        self.assertEqual(c.total_obligated, 120_000)
        self.assertEqual(c.total_consumed, 80_000)
        self.assertEqual(c.available_to_obligate, 80_000)   # 200k - 120k
        self.assertEqual(c.available_to_consume, 40_000)    # 120k - 80k
        # Legacy fields
        self.assertEqual(c.consumed_amount, 80_000)
        self.assertEqual(c.remaining_amount, 120_000)       # cap 200k - consumed 80k

    # ====================================================================
    # 8. Header positive amount constraint
    # ====================================================================

    def test_70_zero_amount_allowed_in_draft(self):
        """A zero วงเงินอนุมัติ is allowed while draft (staging); it is only
        the จองงบประมาณ step that requires a positive amount (see test_02b)."""
        c = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Test commitment",
                "account_id": self.account_1.id,
                "amount": 0,
                "analytic_distribution": self._header_analytic(),
                "account_fiscal_year_id": self.fiscal_year.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )
        self.assertEqual(c.state, "draft")
        self.assertEqual(c.amount, 0)

    def test_71_negative_amount_fails(self):
        """Commitment cap cannot be negative."""
        with self.assertRaises(UserError):
            self.env["budget.commitment"].create(
                {
                    "date": date.today(),
                "title": "Test commitment",
                    "account_id": self.account_1.id,
                    "amount": -1,
                    "analytic_distribution": self._header_analytic(),
                    "account_fiscal_year_id": self.fiscal_year.id,
                    "company_id": self.env.company.id,
                    "currency_id": self.env.company.currency_id.id,
                }
            )

    # ====================================================================
    # 9. Full workflow: reserve -> obligate -> consume -> done
    # ====================================================================

    def test_80_full_lifecycle(self):
        """Complete lifecycle: reserve, obligate all, consume all, close."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self.assertEqual(c.state, "reserved")

        self._add_line(c, "obligate", 100_000)
        self.assertEqual(c.state, "partial")
        self.assertEqual(c.available_to_obligate, 0)

        self._add_line(c, "consume", 100_000)
        self.assertEqual(c.available_to_consume, 0)
        self.assertTrue(c.line_ids.filtered(
            lambda l: l.move_type == "consume" and l.budget_move_id
        ))

        c.action_done()
        self.assertEqual(c.state, "done")

    # ====================================================================
    # 10. State transition guards
    # ====================================================================

    def test_90_reserve_only_from_draft(self):
        """action_reserve only works from draft."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        with self.assertRaises(UserError):
            c.action_reserve()

    def test_91_done_not_from_draft(self):
        """Cannot close a draft commitment."""
        c = self._create_commitment(100_000)
        with self.assertRaises(UserError):
            c.action_done()

    def test_92_cancel_done_fails(self):
        """Cannot cancel a done commitment."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        c.action_done()
        with self.assertRaises(UserError):
            c.action_cancel()

    def test_93_reset_only_from_cancel(self):
        """action_reset_to_draft only works from cancel."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        with self.assertRaises(UserError):
            c.action_reset_to_draft()

    # ====================================================================
    # 11. Cancel recalculates balances
    # ====================================================================

    def test_100_cancel_line_recalculates(self):
        """Cancelling a line recalculates commitment totals."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        obl = self._add_line(c, "obligate", 60_000)
        self.assertEqual(c.available_to_obligate, 40_000)

        obl.action_cancel()
        self.assertEqual(c.total_obligated, 0)
        self.assertEqual(c.available_to_obligate, 100_000)

    # ====================================================================
    # 12. Cross-year carry-over fields exist
    # ====================================================================

    def test_110_carry_over_fields(self):
        """carry-over fields exist and default to empty."""
        c = self._create_commitment(100_000)
        self.assertFalse(c.carried_over_from_id)
        self.assertFalse(c.carried_over_to_id)

    # ====================================================================
    # 13. Partial operations with multiple lines
    # ====================================================================

    def test_120_multiple_obligate_lines(self):
        """Multiple obligate lines accumulate correctly."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 30_000)
        self._add_line(c, "obligate", 20_000)
        self._add_line(c, "obligate", 10_000)
        self.assertEqual(c.total_obligated, 60_000)
        self.assertEqual(c.available_to_obligate, 40_000)

    def test_121_multiple_consume_lines(self):
        """Multiple consume lines each create their own budget.move."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 100_000)
        c1 = self._add_line(c, "consume", 20_000)
        c2 = self._add_line(c, "consume", 30_000)
        self.assertEqual(c.total_consumed, 50_000)
        self.assertNotEqual(c1.budget_move_id, c2.budget_move_id)
        self.assertEqual(len(c.budget_move_ids), 2)

    # ====================================================================
    # 14. Phase 1 — state-machine guards & auto-transitions
    # ====================================================================

    def test_200_b1_block_obligate_on_draft(self):
        """B1: a forward obligate is rejected while the commitment is draft."""
        c = self._create_commitment(100_000)  # stays draft (no action_reserve)
        with self.assertRaises(UserError):
            self._add_line(c, "obligate", 50_000)

    def test_201_b3_auto_done_on_full_consume(self):
        """B3: state auto-advances to done when consumption reaches the reservation."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 100_000)
        self.assertEqual(c.state, "partial")
        self._add_line(c, "consume", 100_000)
        self.assertEqual(c.state, "done")

    def test_202_b3_revert_to_reserved_on_cancel(self):
        """B3: cancelling the only obligation reverts partial -> reserved."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        ob = self._add_line(c, "obligate", 40_000)
        self.assertEqual(c.state, "partial")
        ob.action_cancel()
        self.assertEqual(c.state, "reserved")

    def test_203_b1_reversal_allowed_after_done(self):
        """B1: a refund (negative consume) is postable after done and reopens it."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        self._add_line(c, "obligate", 100_000)
        self._add_line(c, "consume", 100_000)
        self.assertEqual(c.state, "done")
        # Negative consume = refund: allowed even though state is done.
        self._add_line(c, "consume", -10_000)
        self.assertEqual(c.total_consumed, 90_000)
        self.assertEqual(c.state, "partial")  # auto-reopened by _sync_state

    def test_204_b2_negative_net_total_blocked(self):
        """B2: a reversal that drives a net total below zero is rejected."""
        c = self._create_commitment(100_000)
        c.action_reserve()
        # Nothing consumed yet; a -10k consume would make total_consumed negative.
        with self.assertRaises(ValidationError):
            self._add_line(c, "consume", -10_000)

    def test_205_appropriation_move_defaults_initial(self):
        """FIX-1: appropriation moves auto-get 'initial'; entry/explicit are untouched."""
        Move = self.env["budget.move"]
        appro = Move.create({"move_type": "appropriation", "budget_type": "expense"})
        self.assertEqual(appro.appropriation_type, "initial")
        entry = Move.create({"move_type": "entry", "budget_type": "expense"})
        self.assertFalse(entry.appropriation_type)
        explicit = Move.create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "supplementary",
            }
        )
        self.assertEqual(explicit.appropriation_type, "supplementary")

    # ====================================================================
    # 6. Return leftover reserved budget (ส่งคืนเงินเหลือจ่าย / คืนจอง)
    # ====================================================================

    def _return_wizard(self, commitment, **ctx):
        """Open + return the leftover via the confirmation wizard."""
        action = commitment.action_return_leftover()
        self.assertEqual(action["res_model"], "budget.commitment.return.wizard")
        wizard = (
            self.env["budget.commitment.return.wizard"]
            .with_context(**action["context"], **ctx)
            .create({})
        )
        return wizard

    def test_60_return_leftover_releases_reservation(self):
        """Returning the leftover posts a -reserve line and closes the commitment."""
        c = self._create_commitment(600)
        c.action_reserve()
        # Disburse 550 (obligate + consume together, like the DR flow).
        self._add_line(c, "obligate", 550)
        self._add_line(c, "consume", 550)
        self.assertEqual(c.available_to_obligate, 50)
        self.assertEqual(c.state, "partial")
        wizard = self._return_wizard(c)
        self.assertEqual(wizard.return_amount, 50)
        wizard.action_confirm()
        # Reserved dropped to consumed; leftover back in the pool; commitment done.
        self.assertEqual(c.total_reserved, 550)
        self.assertEqual(c.available_to_obligate, 0)
        self.assertEqual(c.state, "done")
        ret = c.line_ids.filtered(lambda l: l.is_return)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret.move_type, "reserve")
        self.assertEqual(ret.amount, -50)
        self.assertFalse(ret.budget_move_id)  # no GL/budget move for คืนจอง

    def test_61_return_inherits_reserve_account_and_dims(self):
        """The return line mirrors the first reserve line's account + dimensions."""
        c = self._create_commitment(600)
        c.action_reserve()
        self._add_line(c, "obligate", 500)
        self._add_line(c, "consume", 500)
        self._return_wizard(c).action_confirm()
        ret = c.line_ids.filtered(lambda l: l.is_return)
        self.assertEqual(ret.account_id, c.account_id)
        self.assertEqual(ret.analytic_distribution, self._line_analytic())

    def test_62_return_stamps_source_document_from_context(self):
        """A return opened from a source doc stamps res_model/res_id for audit."""
        c = self._create_commitment(600)
        c.action_reserve()
        self._add_line(c, "obligate", 550)
        self._add_line(c, "consume", 550)
        wizard = self._return_wizard(
            c, default_res_model="budget.commitment", default_res_id=c.id
        )
        wizard.action_confirm()
        ret = c.line_ids.filtered(lambda l: l.is_return)
        self.assertEqual(ret.res_model, "budget.commitment")
        self.assertEqual(ret.res_id, c.id)

    def test_63_return_blocked_when_nothing_left(self):
        """No leftover -> the action refuses to open the wizard."""
        c = self._create_commitment(600)
        c.action_reserve()
        self._add_line(c, "obligate", 600)
        self._add_line(c, "consume", 600)
        self.assertEqual(c.available_to_obligate, 0)
        with self.assertRaises(UserError):
            c.action_return_leftover()
