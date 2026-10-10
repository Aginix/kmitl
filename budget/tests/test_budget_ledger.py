from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


class BudgetLedgerCommon(TransactionCase):
    """Commitment events posted to the budget ledger (budget ADR-0016)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        # kmitl_demo enables negative budgets; the blocking paths need it off.
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", False)
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-LEDGER",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.parent = BA.create(
            {
                "code": "LDG00",
                "name": "Ledger Parent",
                "budget_type": "expense",
                "budgetable": False,
            }
        )
        cls.account = BA.create(
            {
                "code": "LDG01",
                "name": "Ledger Child",
                "budget_type": "expense",
                "budgetable": True,
                "parent_id": cls.parent.id,
            }
        )
        # A kmitl_project tag is only accepted on a project budget code.
        if "is_project" in BA._fields:
            cls.account.write({"is_project": True, "project_type": "project"})
        cls.other = BA.create(
            {
                "code": "LDG02",
                "name": "Ledger Other",
                "budget_type": "expense",
                "budgetable": True,
                "parent_id": cls.parent.id,
            }
        )
        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, code, plan_code):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            return AA.create({"name": name, "code": code, "plan_id": plan.id})

        cls.dept = acc("Ledger Dept", "LDG_DEPT", "departments")
        cls.source = acc("Ledger Source", "LDG_SRC", "sources")
        cls.activity = acc("Ledger Activity", "LDG_ACT", "activities")
        cls.fund = acc("Ledger Fund", "LDG_FUND", "funds")
        cls.tag = acc("Ledger Project", "LDG_PROJ", "kmitl_project")
        cls.controller = env["budget.controller"]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _distribution(self, tag=None, activity=None):
        accounts = [self.dept, self.source, activity or self.activity, self.fund]
        if tag:
            accounts.append(tag)
        return {str(a.id): 100.0 for a in accounts}

    def _appropriate(self, amount, account=None, tag=None, activity=None):
        line = {
            "account_id": (account or self.account).id,
            "balance": amount,
            "activity_analytic_id": (activity or self.activity).id,
            "fund_analytic_id": self.fund.id,
        }
        if tag:
            line["kmitl_project_analytic_id"] = tag.id
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "line_ids": [Command.create(line)],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _reserve(self, amount, tag=None, account=None, activity=None):
        commitment = self._draft(amount, tag=tag, account=account, activity=activity)
        commitment.action_reserve()
        return commitment

    def _draft(self, amount, tag=None, account=None, activity=None):
        return self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Ledger commitment",
                "account_id": (account or self.account).id,
                "amount": amount,
                "analytic_distribution": self._distribution(tag, activity),
                "account_fiscal_year_id": self.fy.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )

    def _available(self, tag=None, account=None, activity=None):
        return self.controller.get_available(
            account or self.account, self._distribution(tag, activity), self.fy.id
        )

    def _buckets(self, commitment):
        return commitment._ledger_buckets()


@tagged("post_install", "-at_install")
class TestBudgetLedger(BudgetLedgerCommon):
    """Commitment events posted to the budget ledger (ADR-0016)."""

    # ------------------------------------------------------------------
    # posting (Q2)
    # ------------------------------------------------------------------
    def test_reserve_posts_to_ledger(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        lines = commitment.ledger_line_ids
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.move_type, "reserve")
        self.assertEqual(lines.balance, -60_000)
        self.assertEqual(lines.move_id.move_type, "reserve")
        self.assertEqual(lines.move_id.state, "posted")
        self.assertEqual(lines.department_analytic_id, self.dept)
        self.assertEqual(lines.source_analytic_id, self.source)
        self.assertEqual(commitment.total_reserved, 60_000)
        self.assertEqual(commitment.available_to_obligate, 60_000)
        self.assertEqual(self._available(), 40_000)

    def test_obligate_then_consume_liquidates(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("obligate", 40_000)
        commitment._post_budget_event("consume", 25_000)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -20_000, "obligate": -15_000, "consume": -25_000},
        )
        self.assertEqual(commitment.available_to_obligate, 20_000)
        self.assertEqual(commitment.available_to_consume, 15_000)
        self.assertEqual(commitment.total_obligated, 40_000)
        self.assertEqual(commitment.total_consumed, 25_000)
        self.assertEqual(commitment.total_reserved, 60_000)
        self.assertEqual(commitment.state, "partial")
        # Σ balance of everything posted = Remaining (f)
        self.assertEqual(self._available(), 40_000)

    def test_consume_without_obligation_releases_reserve(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("consume", 30_000)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -30_000, "obligate": 0.0, "consume": -30_000},
        )
        self.assertEqual(commitment.total_obligated, 30_000)
        self.assertEqual(commitment.available_to_obligate, 30_000)
        self.assertEqual(self._available(), 40_000)

    def test_consume_keeps_other_documents_obligation(self):
        """A document that obligated nothing liquidates the reserve, never
        another document's obligation on the shared reservation."""
        self._appropriate(100_000)
        commitment = self._reserve(100_000)
        commitment._post_budget_event("obligate", 30_000, source=self.fy)
        commitment._post_budget_event("consume", 50_000, source=self.account)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -20_000, "obligate": -30_000, "consume": -50_000},
        )

    def test_refund_mirrors_reserve_liquidation(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("consume", 50_000, source=self.fy)
        commitment._post_budget_event("consume", -20_000, source=self.fy)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -30_000, "obligate": 0.0, "consume": -30_000},
        )
        self.assertNotIn(commitment, commitment._ledger_mismatches())

    def _cross_charge_reservation(self):
        """ถัวจ่าย: primary code 60,000 on the header + other code 40,000."""
        (self.account | self.other).write({"cross_chargeable": True})
        self._appropriate(100_000)
        self._appropriate(100_000, account=self.other)
        commitment = self._draft(100_000)
        for account, amount in ((self.account, 60_000), (self.other, 40_000)):
            self.env["budget.commitment.line"].create(
                {
                    "commitment_id": commitment.id,
                    "move_type": "reserve",
                    "account_id": account.id,
                    "amount": amount,
                    "analytic_distribution": commitment.analytic_distribution,
                }
            )
        commitment.action_reserve()
        return commitment

    def _consumed_per_code(self, commitment):
        consumed = {}
        for line in commitment.ledger_line_ids:
            if line.parent_state == "posted" and line.move_type == "consume":
                consumed[line.account_id] = (
                    consumed.get(line.account_id, 0.0) - line.balance
                )
        return consumed

    def test_cross_charge_liquidates_primary_code_first(self):
        """ถัวจ่าย (ADR-0017): consume draws the primary code first, the
        return gives back what the next code still holds."""
        commitment = self._cross_charge_reservation()
        commitment._post_budget_event("consume", 70_000)
        self.assertEqual(
            self._consumed_per_code(commitment),
            {self.account: 60_000, self.other: 10_000},
        )
        self.env["budget.commitment.return.wizard"].create(
            {"commitment_id": commitment.id}
        ).action_confirm()
        self.assertEqual(commitment.total_consumed, 70_000)
        self.assertEqual(commitment.available_to_obligate, 0.0)
        self.assertEqual(self._available(), 40_000)  # primary: 60 spent
        self.assertEqual(self._available(account=self.other), 90_000)  # 10 spent

    def test_cross_charge_refund_credits_primary_code(self):
        commitment = self._cross_charge_reservation()
        commitment._post_budget_event("consume", 70_000)
        commitment._post_budget_event("consume", -20_000)
        self.assertEqual(
            self._consumed_per_code(commitment),
            {self.account: 40_000, self.other: 10_000},
        )
        # beyond what the primary consumed, the refund moves on to the next code
        commitment._post_budget_event("consume", -45_000)
        self.assertEqual(
            self._consumed_per_code(commitment),
            {self.account: 0.0, self.other: 5_000},
        )

    def test_batch_reserve_checks_each_against_the_pool(self):
        self._appropriate(100_000)
        batch = self._draft(80_000) | self._draft(80_000)
        with self.assertRaises(UserError):
            batch.action_reserve()

    def test_mixin_consume_creates_no_extra_move(self):
        """The consume event's own move replaces the old consume-only move."""
        self._appropriate(100_000)
        commitment = self._reserve(10_000)
        commitment._post_budget_event("obligate", 10_000)
        event = commitment._post_budget_event("consume", 10_000)
        self.assertEqual(event.budget_move_id.move_type, "consume")
        self.assertEqual(len(commitment.ledger_line_ids.move_id), 3)
        self.assertEqual(commitment.state, "done")

    def test_return_leftover(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("obligate", 25_000)
        commitment._post_budget_event("consume", 25_000)
        wizard = self.env["budget.commitment.return.wizard"].create(
            {"commitment_id": commitment.id}
        )
        wizard.action_confirm()
        self.assertEqual(commitment.total_reserved, 25_000)
        self.assertEqual(commitment.available_to_obligate, 0.0)
        self.assertEqual(commitment.state, "done")
        returned = commitment.ledger_line_ids.filtered("is_return")
        self.assertEqual(returned.balance, 35_000)
        self.assertEqual(self._available(), 75_000)

    def test_over_obligation_blocked(self):
        self._appropriate(100_000)
        commitment = self._reserve(10_000)
        with self.assertRaises(ValidationError):
            commitment._post_budget_event("obligate", 12_000)

    def test_reserve_blocked_when_insufficient(self):
        self._appropriate(10_000)
        with self.assertRaises(UserError):
            self._reserve(12_000)

    # ------------------------------------------------------------------
    # cancellation + per-document lookup (Q6/Q8)
    # ------------------------------------------------------------------
    def test_cancel_document_events(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        source = self.fy  # any record stands in for the source document
        commitment._post_budget_event("obligate", 20_000, source=source)
        commitment._post_budget_event("consume", 20_000, source=source)
        self.assertTrue(commitment._has_budget_event(source, "obligate"))
        commitment._cancel_budget_events(
            source=source, move_types=("obligate", "consume")
        )
        self.assertFalse(commitment._has_budget_event(source, "obligate"))
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -60_000, "obligate": 0.0, "consume": 0.0},
        )
        self.assertEqual(commitment.state, "reserved")

    def test_cancel_commitment_cancels_its_moves(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("obligate", 20_000)
        commitment.action_cancel()
        self.assertEqual(
            set(commitment.ledger_line_ids.mapped("parent_state")), {"cancel"}
        )
        self.assertEqual(self._available(), 100_000)

    def test_posted_ledger_line_is_locked(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        with self.assertRaises(UserError):
            commitment.ledger_line_ids.write({"balance": -1})

    # ------------------------------------------------------------------
    # consume guard: consumed ≤ obligated per source (Q2)
    # ------------------------------------------------------------------
    def test_second_consume_beyond_own_obligation_blocked(self):
        """Once a source has obligated, a consume past what it obligated is
        blocked — it must not fall back to liquidating the reserve."""
        self._appropriate(100_000)
        commitment = self._reserve(100_000)
        source = self.fy
        commitment._post_budget_event("obligate", 60_000, source=source)
        commitment._post_budget_event("consume", 60_000, source=source)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -40_000, "obligate": 0.0, "consume": -60_000},
        )
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            commitment._post_budget_event("consume", 10_000, source=source)
        self.assertEqual(commitment.total_consumed, 60_000)
        self.assertEqual(commitment.available_to_obligate, 40_000)
        self.assertEqual(self._available(), 0.0)

    def test_second_consume_beyond_obligation_blocked_without_source(self):
        self._appropriate(100_000)
        commitment = self._reserve(100_000)
        commitment._post_budget_event("obligate", 60_000)
        commitment._post_budget_event("consume", 60_000)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            commitment._post_budget_event("consume", 1)

    def test_deobligated_source_consumes_from_reserve(self):
        """A source whose obligation was fully de-obligated is back to
        'never obligated' and draws on the reserve."""
        self._appropriate(100_000)
        commitment = self._reserve(100_000)
        source = self.fy
        commitment._post_budget_event("obligate", 30_000, source=source)
        commitment._post_budget_event("obligate", -30_000, source=source)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -100_000, "obligate": 0.0, "consume": 0.0},
        )
        commitment._post_budget_event("consume", 20_000, source=source)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -80_000, "obligate": 0.0, "consume": -20_000},
        )

    def test_default_consume_amount(self):
        """A consume with no amount takes the open obligation, or the
        unobligated reserve when nothing is obligated."""
        self._appropriate(100_000)
        obligated = self._reserve(40_000)
        obligated._post_budget_event("obligate", 25_000)
        self.controller.consume_budget(obligated.id)
        self.assertEqual(
            self._buckets(obligated),
            {"reserve": -15_000, "obligate": 0.0, "consume": -25_000},
        )
        plain = self._reserve(60_000)
        self.controller.consume_budget(plain.id)
        self.assertEqual(
            self._buckets(plain),
            {"reserve": 0.0, "obligate": 0.0, "consume": -60_000},
        )
        self.assertEqual(plain.state, "done")
        self.assertEqual(self._available(), 0.0)

    # ------------------------------------------------------------------
    # ledger moves are locked (Q4/Q8)
    # ------------------------------------------------------------------
    def test_event_move_cannot_be_reset_cancelled_or_deleted(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        move = commitment.ledger_line_ids.move_id
        for action in (move.button_draft, move.button_cancel, move.unlink):
            with self.assertRaises(UserError):
                action()
        with self.assertRaises(UserError):
            move.write({"move_type": "entry"})
        with self.assertRaises(UserError):
            commitment.ledger_line_ids.unlink()
        with self.assertRaises(UserError):
            commitment.ledger_line_ids.write({"source_analytic_id": False})
        self.assertEqual(move.state, "posted")
        self.assertEqual(commitment.total_reserved, 60_000)
        self.assertEqual(self._available(), 40_000)
        # the commitment's own undo still works
        commitment.action_cancel()
        self.assertEqual(move.state, "cancel")
        self.assertEqual(self._available(), 100_000)

    def test_manual_usage_bucket_move_blocked(self):
        """reserve/obligate/consume moves without a commitment would change
        availability with no reservation behind them: they cannot be posted."""
        self._appropriate(100_000)
        for move_type in ("reserve", "obligate", "consume"):
            move = self.env["budget.move"].create(
                {
                    "move_type": move_type,
                    "budget_type": "expense",
                    "account_fiscal_year_id": self.fy.id,
                    "department_analytic_id": self.dept.id,
                    "source_analytic_id": self.source.id,
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": self.account.id,
                                "balance": -10_000,
                                "activity_analytic_id": self.activity.id,
                                "fund_analytic_id": self.fund.id,
                            }
                        )
                    ],
                }
            )
            move.action_review()
            with self.assertRaises(ValidationError), self.env.cr.savepoint():
                move.action_post()
            self.assertEqual(move.state, "review")
        self.assertEqual(self._available(), 100_000)

    # ------------------------------------------------------------------
    # engine (Q3)
    # ------------------------------------------------------------------
    def test_pool_tags_pinned_symmetrically(self):
        self._appropriate(50_000)
        self._appropriate(100_000, tag=self.tag)
        self._reserve(60_000, tag=self.tag)
        self.assertEqual(self._available(tag=self.tag), 40_000)
        # the untagged pool ignores the tagged reservation entirely
        self.assertEqual(self._available(), 50_000)

    def test_floating_tagged_reservation_reported(self):
        """A tagged reservation made against the untagged floating pool
        (ADR-0007, before the money moved onto the tag) leaves its tag
        coordinate negative once tags are pinned; the reconciliation names it
        instead of silently freeing the money on the untagged pool."""
        self._appropriate(100_000)
        self.env["ir.config_parameter"].sudo().set_param(
            "budget.allow_negative", True
        )
        floating = self._reserve(60_000, tag=self.tag)
        self.env["ir.config_parameter"].sudo().set_param(
            "budget.allow_negative", False
        )
        self.assertEqual(self._available(tag=self.tag), -60_000)
        self.assertEqual(floating._ledger_tag_shortfall(), 60_000)
        self.assertIn(floating, floating._ledger_mismatches())
        report = self.env["budget.ledger.reconcile"].action_open_reconciliation()
        rows = self.env["budget.ledger.reconcile"].search(report["domain"])
        row = rows.filtered(lambda r: r.commitment_id == floating)
        self.assertEqual(row.difference, -60_000)
        self.assertEqual(row.kmitl_project_analytic_id, self.tag)

    def test_funded_tagged_reservation_not_reported(self):
        self._appropriate(100_000, tag=self.tag)
        funded = self._reserve(60_000, tag=self.tag)
        self.assertEqual(funded._ledger_tag_shortfall(), 0.0)
        self.assertNotIn(funded, funded._ledger_mismatches())

    # ------------------------------------------------------------------
    # back-fill + reconciliation (Q11)
    # ------------------------------------------------------------------
    def test_backfill_rebuilds_history_and_reconciles(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("obligate", 40_000)
        consume = commitment._post_budget_event("consume", 25_000)
        # Rewind to the pre-ledger world: no ledger postings, and the consume
        # event carrying its old consume-only move.
        moves = commitment.ledger_line_ids.move_id
        commitment.line_ids.write(
            {"budget_move_id": False, "budget_move_line_id": False}
        )
        moves.with_context(budget_ledger_posting=True).unlink()
        legacy_move = self.env["budget.move"].with_context(
            budget_ledger_posting=True
        ).create(
            {
                "date": consume.date,
                "move_type": "consume",
                "budget_type": "expense",
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "commitment_id": commitment.id,
                "commitment_line_id": consume.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": consume.account_id.id,
                            "balance": -25_000,
                            "analytic_distribution": consume.analytic_distribution,
                        }
                    )
                ],
            }
        )
        legacy_move.action_review()
        legacy_move.action_post()
        consume.budget_move_id = legacy_move
        self.assertFalse(commitment.ledger_line_ids.filtered("commitment_line_id"))

        mismatched = (
            self.env["budget.commitment"]
            .with_context(budget_ledger_posting=True)
            ._ledger_backfill()
        )

        self.assertNotIn(commitment, mismatched)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -20_000, "obligate": -15_000, "consume": -25_000},
        )
        self.assertEqual(consume.budget_move_id, legacy_move)
        self.assertEqual(len(legacy_move.line_ids), 2)
        self.assertEqual(self._available(), 40_000)

        report = self.env["budget.ledger.reconcile"].action_open_reconciliation()
        rows = self.env["budget.ledger.reconcile"].search(report["domain"])
        self.assertFalse(rows.filtered(lambda r: r.commitment_id == commitment))
        self.assertFalse(rows.filtered(lambda r: r.account_id == self.account))

    # ------------------------------------------------------------------
    # back-fill of other histories (Q11)
    # ------------------------------------------------------------------
    def _snapshot(self, commitment, accounts):
        commitment.invalidate_recordset()
        return (
            self._buckets(commitment),
            self._consumed_per_code(commitment),
            [self._available(account=account) for account in accounts],
        )

    def _rewind_to_legacy(self, commitment):
        """Undo the ledger posting of ``commitment`` back to the pre-ledger
        world: no event moves, each consume event with its old consume-only
        move on the event's own code."""
        events = commitment.line_ids.filtered(lambda line: line.state == "posted")
        moves = commitment.ledger_line_ids.move_id
        events.write({"budget_move_id": False, "budget_move_line_id": False})
        moves.with_context(budget_ledger_posting=True).unlink()
        Move = self.env["budget.move"].with_context(budget_ledger_posting=True)
        for event in events.filtered(lambda line: line.move_type == "consume"):
            legacy = Move.create(
                {
                    "date": event.date,
                    "move_type": "consume",
                    "budget_type": "expense",
                    "account_fiscal_year_id": self.fy.id,
                    "department_analytic_id": self.dept.id,
                    "source_analytic_id": self.source.id,
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": event.account_id.id,
                                "balance": -event.amount,
                                "analytic_distribution": event.analytic_distribution,
                            }
                        )
                    ],
                }
            )
            legacy.action_review()
            legacy.action_post()
            event.budget_move_id = legacy
        commitment.invalidate_recordset()
        self.assertFalse(commitment.ledger_line_ids.filtered("commitment_line_id"))

    def _backfill(self):
        return (
            self.env["budget.commitment"]
            .with_context(budget_ledger_posting=True)
            ._ledger_backfill()
        )

    def test_backfill_return_leftover(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("obligate", 25_000)
        commitment._post_budget_event("consume", 25_000)
        self.env["budget.commitment.return.wizard"].create(
            {"commitment_id": commitment.id}
        ).action_confirm()
        before = self._snapshot(commitment, [self.account])
        self.assertEqual(before[2], [75_000])
        self._rewind_to_legacy(commitment)
        self.assertNotIn(commitment, self._backfill())
        self.assertEqual(self._snapshot(commitment, [self.account]), before)
        self.assertEqual(commitment.ledger_line_ids.filtered("is_return").balance, 35_000)

    def test_backfill_cross_charge_consume_split(self):
        commitment = self._cross_charge_reservation()
        commitment._post_budget_event("consume", 70_000)
        self.env["budget.commitment.return.wizard"].create(
            {"commitment_id": commitment.id}
        ).action_confirm()
        accounts = [self.account, self.other]
        before = self._snapshot(commitment, accounts)
        self.assertEqual(before[1], {self.account: 60_000, self.other: 10_000})
        self._rewind_to_legacy(commitment)
        self.assertNotIn(commitment, self._backfill())
        self.assertEqual(self._snapshot(commitment, accounts), before)

    def test_backfill_legacy_disbursement_obligate_consume_pair(self):
        """Before ADR-0016 a DR posted obligate + consume of the same amount;
        a later document consumed straight from the reserve."""
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("obligate", 30_000, source=self.fy)
        commitment._post_budget_event("consume", 30_000, source=self.fy)
        commitment._post_budget_event("consume", 10_000, source=self.account)
        before = self._snapshot(commitment, [self.account])
        self.assertEqual(
            before[0], {"reserve": -20_000, "obligate": 0.0, "consume": -40_000}
        )
        self._rewind_to_legacy(commitment)
        self.assertNotIn(commitment, self._backfill())
        self.assertEqual(self._snapshot(commitment, [self.account]), before)

    def test_backfill_failing_event_reported_not_aborted(self):
        self._appropriate(100_000)
        broken = self._reserve(30_000)
        fine = self._reserve(20_000)
        self._rewind_to_legacy(broken)
        self._rewind_to_legacy(fine)
        Line = type(self.env["budget.commitment.line"])
        original = Line._ledger_backfill_post

        def post(event):
            if event.commitment_id == broken:
                raise UserError("boom")
            return original(event)

        with patch.object(Line, "_ledger_backfill_post", post):
            mismatched = self._backfill()
        self.assertIn(broken, mismatched)
        self.assertNotIn(fine, mismatched)
        self.assertEqual(broken.total_reserved, 0.0)
        self.assertEqual(fine.total_reserved, 20_000)
        self.assertEqual(self._available(), 80_000)


@tagged("post_install", "-at_install")
class TestBudgetLedgerHierarchy(BudgetLedgerCommon):
    """Appropriation at a funded ancestor covers the reservations of every
    descendant from one pool (ADR-0005 control node), on the budget-code axis
    and on the analytic hierarchy alike."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        BA = cls.env["budget.account"]
        cls.grand = BA.create(
            {
                "code": "LDH00",
                "name": "Hierarchy Root",
                "budget_type": "expense",
                "budgetable": False,
            }
        )
        cls.pool = BA.create(
            {
                "code": "LDH10",
                "name": "Funded Parent",
                "budget_type": "expense",
                "budgetable": True,
                "parent_id": cls.grand.id,
            }
        )
        cls.c1, cls.c2 = (
            BA.create(
                {
                    "code": code,
                    "name": "Funded Child %s" % code,
                    "budget_type": "expense",
                    "budgetable": True,
                    "cross_chargeable": True,
                    "parent_id": cls.pool.id,
                }
            )
            for code in ("LDH11", "LDH12")
        )
        AA = cls.env["account.analytic.account"]
        if "parent_id" in AA._fields:
            cls.act_root = AA.create(
                {
                    "name": "Ledger Activity Root",
                    "code": "LDH_ACT",
                    "plan_id": cls.activity.plan_id.id,
                }
            )
            cls.act_a1, cls.act_a2 = (
                AA.create(
                    {
                        "name": "Ledger Activity %s" % code,
                        "code": code,
                        "plan_id": cls.activity.plan_id.id,
                        "parent_id": cls.act_root.id,
                    }
                )
                for code in ("LDH_ACT1", "LDH_ACT2")
            )

    def _dashboard(self):
        return {
            row["id"]: row
            for row in self.env["budget.dashboard"].get_dashboard_data(
                self.fy.id, self.grand.id
            )["rows"]
        }

    def test_parent_pool_shared_by_child_codes(self):
        self._appropriate(100_000, account=self.pool)
        r1 = self._reserve(30_000, account=self.c1)
        self._reserve(50_000, account=self.c2)
        for account in (self.c1, self.c2, self.pool):
            self.assertEqual(self._available(account=account), 20_000)
        # a sibling cannot take more than what the shared pool has left
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self._reserve(30_000, account=self.c1)
        # spending a reservation does not change the pool; returning does
        r1._post_budget_event("consume", 10_000)
        self.assertEqual(self._available(account=self.c2), 20_000)
        self.env["budget.commitment.return.wizard"].create(
            {"commitment_id": r1.id}
        ).action_confirm()
        self.assertEqual(r1.total_reserved, 10_000)
        self.assertEqual(self._available(account=self.c2), 40_000)

    def test_cross_charge_codes_checked_against_one_parent_pool(self):
        """ถัวจ่าย codes under the same funded parent are summed against that
        pool, not each checked against the whole of it."""
        self._appropriate(100_000, account=self.pool)

        def cross_charge(cap, amounts):
            commitment = self._draft(cap, account=self.c1)
            for account, amount in zip((self.c1, self.c2), amounts):
                self.env["budget.commitment.line"].create(
                    {
                        "commitment_id": commitment.id,
                        "move_type": "reserve",
                        "account_id": account.id,
                        "amount": amount,
                        "analytic_distribution": commitment.analytic_distribution,
                    }
                )
            return commitment

        over = cross_charge(130_000, (70_000, 60_000))
        with self.assertRaises(UserError):
            over.action_reserve()
        self.assertEqual(over.state, "draft")
        self.assertFalse(over.ledger_line_ids)
        self.assertEqual(self._available(account=self.pool), 100_000)

        exact = cross_charge(100_000, (60_000, 40_000))
        exact.action_reserve()
        self.assertEqual(exact.total_reserved, 100_000)
        self.assertEqual(self._available(account=self.pool), 0.0)

    def test_dashboard_rolls_ledger_up_to_funded_parent(self):
        self._appropriate(100_000, account=self.pool)
        r1 = self._reserve(30_000, account=self.c1)
        r1._post_budget_event("obligate", 10_000)
        r2 = self._reserve(50_000, account=self.c2)
        r2._post_budget_event("consume", 20_000)
        rows = self._dashboard()
        c1, c2, pool = rows[self.c1.id], rows[self.c2.id], rows[self.pool.id]
        self.assertEqual(
            (c1["reserved"], c1["obligated"], c1["consumed"], c1["used"]),
            (20_000, 10_000, 0.0, 30_000),
        )
        self.assertEqual(
            (c2["reserved"], c2["obligated"], c2["consumed"], c2["used"]),
            (30_000, 0.0, 20_000, 50_000),
        )
        self.assertEqual(pool["current"], 100_000)
        self.assertEqual(
            (pool["reserved"], pool["obligated"], pool["consumed"]),
            (50_000, 10_000, 20_000),
        )
        self.assertEqual(pool["used"], 80_000)
        self.assertEqual(pool["remaining"], 20_000)
        self.assertEqual(pool["cap"], 80_000)
        # the remaining at the pool is exactly what the engine lets a child take
        self.assertEqual(pool["remaining"], self._available(account=self.c1))
        grand = rows[self.grand.id]
        for key in ("current", "reserved", "obligated", "consumed", "remaining"):
            self.assertEqual(grand[key], pool[key])

    def test_activity_parent_pool_shared_by_child_activities(self):
        if "parent_id" not in self.env["account.analytic.account"]._fields:
            self.skipTest("analytic hierarchy (account_analytic_parent) absent")
        self._appropriate(100_000, activity=self.act_root)
        self._reserve(60_000, activity=self.act_a1)
        for activity in (self.act_a1, self.act_a2, self.act_root):
            self.assertEqual(self._available(activity=activity), 40_000)
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self._reserve(50_000, activity=self.act_a2)
        self._reserve(40_000, activity=self.act_a2)
        self.assertEqual(self._available(activity=self.act_root), 0.0)
        # an unrelated activity never sees that pool
        self.assertEqual(self._available(), 0.0)
