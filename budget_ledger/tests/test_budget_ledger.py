from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetLedger(TransactionCase):
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
    def _distribution(self, tag=None):
        accounts = [self.dept, self.source, self.activity, self.fund]
        if tag:
            accounts.append(tag)
        return {str(a.id): 100.0 for a in accounts}

    def _appropriate(self, amount, account=None, tag=None):
        line = {
            "account_id": (account or self.account).id,
            "balance": amount,
            "activity_analytic_id": self.activity.id,
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

    def _reserve(self, amount, tag=None):
        commitment = self._draft(amount, tag=tag)
        commitment.action_reserve()
        return commitment

    def _draft(self, amount, tag=None):
        return self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Ledger commitment",
                "account_id": self.account.id,
                "amount": amount,
                "analytic_distribution": self._distribution(tag),
                "account_fiscal_year_id": self.fy.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )

    def _available(self, tag=None, account=None):
        return self.controller.get_available(
            account or self.account, self._distribution(tag), self.fy.id
        )

    def _buckets(self, commitment):
        return commitment._ledger_buckets()

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

    def test_cross_charge_liquidates_primary_code_first(self):
        """ถัวจ่าย (ADR-0017): consume draws the primary code first, the
        return gives back what the next code still holds."""
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
        commitment._post_budget_event("consume", 70_000)
        self.env["budget.commitment.return.wizard"].create(
            {"commitment_id": commitment.id}
        ).action_confirm()
        self.assertEqual(commitment.total_consumed, 70_000)
        self.assertEqual(commitment.available_to_obligate, 0.0)
        self.assertEqual(self._available(), 40_000)  # primary: 60 spent
        self.assertEqual(self._available(account=self.other), 90_000)  # 10 spent

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
    # engine (Q3)
    # ------------------------------------------------------------------
    def test_pool_tags_pinned_symmetrically(self):
        self._appropriate(50_000)
        self._appropriate(100_000, tag=self.tag)
        self._reserve(60_000, tag=self.tag)
        self.assertEqual(self._available(tag=self.tag), 40_000)
        # the untagged pool ignores the tagged reservation entirely
        self.assertEqual(self._available(), 50_000)

    def test_dashboard_reads_ledger(self):
        self._appropriate(100_000)
        commitment = self._reserve(60_000)
        commitment._post_budget_event("obligate", 40_000)
        commitment._post_budget_event("consume", 25_000)
        rows = {
            row["id"]: row
            for row in self.env["budget.dashboard"].get_dashboard_data(
                self.fy.id, self.parent.id
            )["rows"]
        }
        child = rows[self.account.id]
        self.assertEqual(child["reserved"], 20_000)
        self.assertEqual(child["obligated"], 15_000)
        self.assertEqual(child["consumed"], 25_000)
        self.assertEqual(child["used"], 60_000)
        self.assertEqual(child["remaining"], 40_000)
        self.assertEqual(child["cap"], 60_000)

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
        moves.unlink()
        consume._create_budget_move()
        legacy_move = consume.budget_move_id
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
