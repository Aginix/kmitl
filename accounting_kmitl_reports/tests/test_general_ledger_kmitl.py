# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from collections import defaultdict

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

REPORT = "report.accounting_kmitl_reports.general_ledger_kmitl"


@tagged("post_install", "-at_install")
class TestGeneralLedgerKmitl(TransactionCase):
    """The Thai General Ledger is a balance-form report: one row per line of
    the account being viewed, using that line's own debit/credit. The
    counterpart account names the Account column and may split a line into
    one row per counterpart, but never drives the amount -- the parts always
    add back to the line's own debit/credit, so every account's totals tie
    out to its own ``account.move.line`` rows, matching the Trial Balance.
    See ``accounting_kmitl_reports/CONTEXT.md`` (Compound entry).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["account.move"]
        cls.Report = cls.env[REPORT]
        cls.company = cls.env.company
        cls.today = fields.Date.context_today(cls.env.user)

        cls.journal = cls.env["account.journal"].create(
            {
                "name": "GL Test Journal",
                "type": "general",
                "code": "GLTST",
                "company_id": cls.company.id,
            }
        )

        def account(name, account_type):
            return cls.env["account.account"].create(
                {
                    "name": name,
                    "code": cls._next_code(),
                    "account_type": account_type,
                    "company_id": cls.company.id,
                }
            )

        cls.expense_a = account("GL Test Expense A", "expense")
        cls.expense_b = account("GL Test Expense B", "expense")
        cls.payable = account("GL Test Payable", "liability_payable")
        cls.receivable = account("GL Test Receivable", "asset_receivable")
        cls.income = account("GL Test Income", "income")
        cls.tax_account = account("GL Test Output Tax", "liability_current")
        cls.cogs = account("GL Test COGS", "expense_direct_cost")
        cls.inventory = account("GL Test Inventory", "asset_current")

    @classmethod
    def _next_code(cls):
        cls._code_seq = getattr(cls, "_code_seq", 899000) + 1
        return str(cls._code_seq)

    # ------------------------------------------------------------------
    def _entry(self, lines, date=None):
        move = self.Move.create(
            {
                "journal_id": self.journal.id,
                "date": date or self.today,
                "line_ids": [(0, 0, line) for line in lines],
            }
        )
        move.action_post()
        return move

    def _data(self, account_ids, **overrides):
        options = {
            "company_id": self.company.id,
            "date_from": fields.Date.to_string(self.today),
            "date_to": fields.Date.to_string(self.today),
            "only_posted": True,
            "hide_account_at_0": False,
            "account_ids": account_ids,
        }
        options.update(overrides)
        return self.Report.get_general_ledger_data(options)

    def _by_code(self, result):
        return {acc["code"]: acc for acc in result["accounts"]}

    # ------------------------------------------------------------------
    def test_two_debit_lines_each_keep_their_own_amount(self):
        """Dr Expense-A 60 / Dr Expense-B 40 / Cr Payable 100 -- before the
        fix, both A and B were credited the payable's full 100 (the
        counterpart's amount), instead of their own line."""
        self._entry(
            [
                {"account_id": self.expense_a.id, "debit": 60.0, "name": "a"},
                {"account_id": self.expense_b.id, "debit": 40.0, "name": "b"},
                {"account_id": self.payable.id, "credit": 100.0, "name": "payable"},
            ]
        )
        accounts = self._by_code(
            self._data([self.expense_a.id, self.expense_b.id, self.payable.id])
        )

        self.assertEqual(accounts[self.expense_a.code]["final_debit"], 60.0)
        self.assertEqual(accounts[self.expense_b.code]["final_debit"], 40.0)
        self.assertEqual(accounts[self.payable.code]["final_credit"], 100.0)

    def test_split_credit_lines_give_one_row_per_counterpart(self):
        """Dr Receivable 100 / Cr Income 93 / Cr Tax 7 -- the receivable's
        single line is shown as one row per counterpart account, each
        carrying that counterpart's own figure, and the two rows add back to
        the line's 100."""
        self._entry(
            [
                {"account_id": self.receivable.id, "debit": 100.0, "name": "ar"},
                {"account_id": self.income.id, "credit": 93.0, "name": "income"},
                {"account_id": self.tax_account.id, "credit": 7.0, "name": "tax"},
            ]
        )
        ar = self._by_code(self._data([self.receivable.id]))[self.receivable.code]

        by_account = {line["account"]: line["debit"] for line in ar["lines"]}
        self.assertEqual(len(ar["lines"]), 2)
        self.assertEqual(
            by_account,
            {
                "%s %s" % (self.income.code, self.income.name): 93.0,
                "%s %s" % (self.tax_account.code, self.tax_account.name): 7.0,
            },
        )
        # The split is presentation only: the rows still foot to the line.
        self.assertEqual(sum(line["debit"] for line in ar["lines"]), 100.0)
        self.assertEqual(ar["lines"][-1]["balance"], 100.0)
        self.assertEqual(ar["final_debit"], 100.0)
        self.assertEqual(ar["final_credit"], 0.0)

    def test_no_split_when_the_counterparts_do_not_add_up_to_the_line(self):
        """Two unrelated settlements in one move (JV/2026/09/0002): the
        withholding-tax debit of 500 faces two credits of 500 each, so the
        entry pairs it with neither. The row must keep its own 500 under both
        names -- never an invented 250/250 apportionment."""
        self._entry(
            [
                {"account_id": self.tax_account.id, "debit": 500.0, "name": "wht"},
                {"account_id": self.receivable.id, "credit": 500.0, "name": "ca-out"},
                {"account_id": self.receivable.id, "debit": 500.0, "name": "ca-in"},
                {"account_id": self.income.id, "credit": 500.0, "name": "sa-out"},
            ]
        )
        accounts = self._by_code(self._data([self.tax_account.id, self.receivable.id]))

        wht = accounts[self.tax_account.code]
        self.assertEqual(len(wht["lines"]), 1)
        self.assertEqual(wht["lines"][0]["debit"], 500.0)
        self.assertEqual(wht["final_debit"], 500.0)
        # Both counterparts named on the one row, no fabricated part amounts.
        self.assertIn(self.receivable.code, wht["lines"][0]["account"])
        self.assertIn(self.income.code, wht["lines"][0]["account"])

        # The account posted on both sides still resolves cleanly: each of its
        # lines faces exactly one counterpart.
        ca = accounts[self.receivable.code]
        self.assertEqual(len(ca["lines"]), 2)
        self.assertEqual(
            {line["account"] for line in ca["lines"]},
            {
                "%s %s" % (self.tax_account.code, self.tax_account.name),
                "%s %s" % (self.income.code, self.income.name),
            },
        )
        self.assertEqual(ca["final_debit"], 500.0)
        self.assertEqual(ca["final_credit"], 500.0)

    def test_rows_add_back_when_both_sides_carry_several_accounts(self):
        """An account with several lines against several counterparts keeps
        one row per line with that line's own amount, so the carried-forward
        stays tied to the Trial Balance."""
        self._entry(
            [
                {"account_id": self.payable.id, "debit": 60.0, "name": "p1"},
                {"account_id": self.payable.id, "debit": 40.0, "name": "p2"},
                {"account_id": self.income.id, "credit": 99.0, "name": "bank"},
                {"account_id": self.tax_account.id, "credit": 1.0, "name": "wht"},
            ]
        )
        payable = self._by_code(self._data([self.payable.id]))[self.payable.code]

        self.assertEqual(
            sorted(line["debit"] for line in payable["lines"]), [40.0, 60.0]
        )
        self.assertEqual(payable["final_debit"], 100.0)
        self.assertEqual(payable["final_credit"], 0.0)
        self.assertEqual(payable["lines"][-1]["balance"], 100.0)

    def test_compound_entry_both_sides_split_each_account_keeps_its_own_lines(self):
        """Express-style compound entry (one invoice + its cost of sale in a
        single move): Dr AR 25680 / Cr Income 24000 / Cr Tax 1680 / Dr COGS
        15000 / Cr Inventory 15000. Every account must show its own amount,
        not a total inflated by the other side."""
        self._entry(
            [
                {"account_id": self.receivable.id, "debit": 25680.0, "name": "ar"},
                {"account_id": self.income.id, "credit": 24000.0, "name": "income"},
                {"account_id": self.tax_account.id, "credit": 1680.0, "name": "tax"},
                {"account_id": self.cogs.id, "debit": 15000.0, "name": "cogs"},
                {"account_id": self.inventory.id, "credit": 15000.0, "name": "inv"},
            ]
        )
        accounts = self._by_code(
            self._data(
                [
                    self.receivable.id,
                    self.income.id,
                    self.tax_account.id,
                    self.cogs.id,
                    self.inventory.id,
                ]
            )
        )

        self.assertEqual(accounts[self.receivable.code]["final_debit"], 25680.0)
        self.assertEqual(accounts[self.income.code]["final_credit"], 24000.0)
        self.assertEqual(accounts[self.tax_account.code]["final_credit"], 1680.0)
        self.assertEqual(accounts[self.cogs.code]["final_debit"], 15000.0)
        self.assertEqual(accounts[self.inventory.code]["final_credit"], 15000.0)

    def test_totals_tie_to_the_account_own_move_lines(self):
        """Every account's final_balance foots to initial + debit - credit,
        and final_debit/final_credit match a plain SUM() of that account's
        own posted ``account.move.line`` rows -- not a value borrowed from
        the entry's other side."""
        self._entry(
            [
                {"account_id": self.expense_a.id, "debit": 60.0, "name": "a"},
                {"account_id": self.expense_b.id, "debit": 40.0, "name": "b"},
                {"account_id": self.payable.id, "credit": 100.0, "name": "payable"},
            ]
        )
        self._entry(
            [
                {"account_id": self.receivable.id, "debit": 100.0, "name": "ar"},
                {"account_id": self.income.id, "credit": 93.0, "name": "income"},
                {"account_id": self.tax_account.id, "credit": 7.0, "name": "tax"},
            ]
        )
        accs = [
            self.expense_a,
            self.expense_b,
            self.payable,
            self.receivable,
            self.income,
            self.tax_account,
        ]
        result = self._data([a.id for a in accs])

        raw_debit, raw_credit = defaultdict(float), defaultdict(float)
        for ml in self.env["account.move.line"].search(
            [
                ("account_id", "in", [a.id for a in accs]),
                ("date", "=", self.today),
                ("move_id.state", "=", "posted"),
                ("display_type", "=", False),
            ]
        ):
            raw_debit[ml.account_id.id] += ml.debit
            raw_credit[ml.account_id.id] += ml.credit

        for acc in result["accounts"]:
            self.assertAlmostEqual(
                acc["final_balance"],
                acc["initial_balance"] + acc["final_debit"] - acc["final_credit"],
            )
            self.assertAlmostEqual(acc["final_debit"], raw_debit[acc["id"]])
            self.assertAlmostEqual(acc["final_credit"], raw_credit[acc["id"]])

    def test_dimension_filter_keeps_only_matching_lines_with_their_own_dimensions(self):
        """Filtering by a fund keeps only the lines carrying that fund, and
        the dimension chips shown come from the matching line itself."""
        Plan = self.env["account.analytic.plan"]
        Analytic = self.env["account.analytic.account"]
        plan = Plan.search([("code", "=", "funds")], limit=1)
        if not plan:
            plan = Plan.create({"name": "Funds", "code": "funds"})
        fund_a = Analytic.create(
            {
                "name": "GL Test Fund A",
                "plan_id": plan.id,
                "company_id": self.company.id,
            }
        )
        fund_b = Analytic.create(
            {
                "name": "GL Test Fund B",
                "plan_id": plan.id,
                "company_id": self.company.id,
            }
        )

        self._entry(
            [
                {
                    "account_id": self.expense_a.id,
                    "debit": 60.0,
                    "name": "a",
                    "analytic_distribution": {str(fund_a.id): 100},
                },
                {
                    "account_id": self.expense_b.id,
                    "debit": 40.0,
                    "name": "b",
                    "analytic_distribution": {str(fund_b.id): 100},
                },
                {"account_id": self.payable.id, "credit": 100.0, "name": "payable"},
            ]
        )

        accounts = self._by_code(
            self._data(
                [self.expense_a.id, self.expense_b.id],
                dims={"funds": [fund_a.id]},
            )
        )

        exp_a = accounts[self.expense_a.code]
        exp_b = accounts[self.expense_b.code]
        self.assertEqual(exp_a["final_debit"], 60.0)
        self.assertEqual(len(exp_a["lines"]), 1)
        dims = exp_a["lines"][0]["dimensions"]
        self.assertTrue(any(d["value"].endswith("GL Test Fund A") for d in dims))
        # expense_b's only line carries fund_b, so it is filtered out entirely.
        self.assertEqual(exp_b["final_debit"], 0.0)
        self.assertFalse(exp_b["lines"])
