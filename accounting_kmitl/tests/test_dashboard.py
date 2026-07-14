# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged

CARD_KEYS = {
    "my_drafts",
    "submitted",
    "unpaid_ap",
    "overdue_ap",
    "unpaid_ar",
    "exceptions",
}
MONEY_CARDS = {"unpaid_ap", "overdue_ap", "unpaid_ar"}


@tagged("post_install", "-at_install")
class TestAccountingDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        accounts = cls.env["account.account"].search(
            [("company_id", "=", cls.company.id)], limit=2
        )
        cls.account_a, cls.account_b = accounts[0], accounts[1]

        group_user = cls.env.ref("accounting_kmitl.group_accounting_kmitl_user")
        account_manager = cls.env.ref("account.group_account_manager")
        cls.maker = cls.env["res.users"].create(
            {
                "name": "Dashboard Maker",
                "login": "kmitl_dashboard_maker",
                "groups_id": [Command.set([group_user.id, account_manager.id])],
            }
        )
        cls.other = cls.env["res.users"].create(
            {
                "name": "Dashboard Other",
                "login": "kmitl_dashboard_other",
                "groups_id": [Command.set([group_user.id, account_manager.id])],
            }
        )
        cls.Dashboard = cls.env["accounting.kmitl.dashboard"]

        # Dedicated accounts for the chart tests.
        def _make_account(code, name, account_type, reconcile=False):
            return cls.env["account.account"].create(
                {
                    "name": name,
                    "code": code,
                    "account_type": account_type,
                    "reconcile": reconcile,
                    "company_id": cls.company.id,
                }
            )

        cls.exp1 = _make_account("TEXP001", "Test Expense 1", "expense")
        cls.exp2 = _make_account("TEXP002", "Test Expense 2", "expense")
        cls.exp3 = _make_account("TEXP003", "Test Expense 3", "expense")
        cls.credit_account = _make_account(
            "TLIA001", "Test Liability", "liability_current"
        )
        cls.income = _make_account("TINC001", "Test Income", "income")
        cls.payable = _make_account(
            "TPAY001", "Test Payable", "liability_payable", reconcile=True
        )
        cls.receivable = _make_account(
            "TREC001", "Test Receivable", "asset_receivable", reconcile=True
        )

        Partner = cls.env["res.partner"]
        cls.vendor_a = Partner.create(
            {"name": "Vendor A", "property_account_payable_id": cls.payable.id}
        )
        cls.vendor_b = Partner.create(
            {"name": "Vendor B", "property_account_payable_id": cls.payable.id}
        )
        cls.customer = Partner.create(
            {
                "name": "Customer A",
                "property_account_receivable_id": cls.receivable.id,
            }
        )

    def _cards_by_id(self, data):
        return {card["id"]: card for card in data["cards"]}

    def _entry(self, user, lines):
        return (
            self.env["account.move"]
            .with_user(user)
            .create(
                {
                    "move_type": "entry",
                    "journal_id": self.journal.id,
                    "date": fields.Date.today(),
                    "line_ids": lines,
                }
            )
        )

    def _balanced_lines(self):
        return [
            Command.create(
                {"account_id": self.account_a.id, "debit": 100.0, "credit": 0.0}
            ),
            Command.create(
                {"account_id": self.account_b.id, "debit": 0.0, "credit": 100.0}
            ),
        ]

    def _self_canceling_lines(self):
        # Same account on both legs, equal amounts -> triggers the pre-defined
        # (non-blocking) self-canceling-pair exception rule on submit.
        return [
            Command.create(
                {"account_id": self.account_a.id, "debit": 100.0, "credit": 0.0}
            ),
            Command.create(
                {"account_id": self.account_a.id, "debit": 0.0, "credit": 100.0}
            ),
        ]

    def _post_expense(self, account, date=None):
        """Create + post a balanced entry that debits ``account``."""
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": date or fields.Date.today(),
                "line_ids": [
                    Command.create(
                        {"account_id": account.id, "debit": 100.0, "credit": 0.0}
                    ),
                    Command.create(
                        {
                            "account_id": self.credit_account.id,
                            "debit": 0.0,
                            "credit": 100.0,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _expense_row(self, account, **kwargs):
        items = (
            self.Dashboard.with_user(self.maker)
            .get_expense_frequency(**kwargs)["items"]
        )
        return next((row for row in items if row["id"] == account.id), None)

    def _post_invoice(self, move_type, partner, amount, due):
        """Create + post an unpaid invoice with a single line and a due date."""
        line_account = self.exp1 if move_type == "in_invoice" else self.income
        move = (
            self.env["account.move"]
            .with_user(self.maker)
            .create(
                {
                    "move_type": move_type,
                    "partner_id": partner.id,
                    "invoice_date": fields.Date.today(),
                    "invoice_date_due": due,
                    "invoice_payment_term_id": False,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "line",
                                "account_id": line_account.id,
                                "quantity": 1.0,
                                "price_unit": amount,
                                "tax_ids": [Command.set([])],
                            }
                        )
                    ],
                }
            )
        )
        move.action_post()
        return move

    def _analytics(self):
        return self.Dashboard.with_user(self.maker).get_analytics()

    def test_structure_and_domain_self_consistency(self):
        """Every card is self-describing and its count equals a fresh
        search_count over its own res_model/domain (money cards also expose
        amount)."""
        data = self.Dashboard.with_user(self.maker).get_dashboard_data()
        self.assertIn("currency_symbol", data)

        cards = self._cards_by_id(data)
        self.assertEqual(set(cards), CARD_KEYS)

        for key, card in cards.items():
            for attr in ("title", "color", "sequence", "res_model", "domain"):
                self.assertIn(attr, card, "%s missing %s" % (key, attr))
            model = self.env[card["res_model"]].with_user(self.maker)
            self.assertEqual(card["count"], model.search_count(card["domain"]), key)
            if key in MONEY_CARDS:
                self.assertIn("amount", card, key)
            else:
                self.assertNotIn("amount", card, key)

        # overdue_ap must be the unpaid_ap domain further narrowed by due date.
        overdue = cards["overdue_ap"]["domain"]
        self.assertTrue(
            any(term[0] == "invoice_date_due" for term in overdue),
            "overdue_ap domain must filter on invoice_date_due",
        )

    def test_my_drafts_scoped_to_current_user(self):
        """my_drafts counts only the caller's own draft documents."""
        before = self.Dashboard.with_user(self.maker).get_dashboard_data()
        base = self._cards_by_id(before)["my_drafts"]["count"]

        self._entry(self.maker, self._balanced_lines())
        self._entry(self.other, self._balanced_lines())  # not the caller's

        after = self.Dashboard.with_user(self.maker).get_dashboard_data()
        self.assertEqual(self._cards_by_id(after)["my_drafts"]["count"], base + 1)

    def test_submitted_card(self):
        """A clean entry submits successfully and shows on the submitted card."""
        move = self._entry(self.maker, self._balanced_lines())
        move.with_user(self.maker).action_submit()
        self.assertEqual(move.state, "submitted")

        data = self.Dashboard.with_user(self.maker).get_dashboard_data()
        self.assertGreaterEqual(self._cards_by_id(data)["submitted"]["count"], 1)

    def test_exception_card(self):
        """Submitting a self-canceling pair is halted (popup) but flags the
        move with an exception, so the exceptions card picks it up."""
        move = self._entry(self.maker, self._self_canceling_lines())
        move.with_user(self.maker).action_submit()  # returns a popup action
        self.assertTrue(move.exception_ids)
        self.assertEqual(move.state, "draft")

        data = self.Dashboard.with_user(self.maker).get_dashboard_data()
        self.assertGreaterEqual(self._cards_by_id(data)["exceptions"]["count"], 1)

    def test_expense_frequency_counts_distinct_documents(self):
        """Two separate posted documents on the same expense account count 2,
        and the row carries the account code/name."""
        self._post_expense(self.exp1)
        self._post_expense(self.exp1)

        row = self._expense_row(self.exp1)
        self.assertIsNotNone(row)
        self.assertEqual(row["count"], 2)
        self.assertEqual(row["code"], self.exp1.code)
        self.assertEqual(row["name"], self.exp1.name)

    def test_expense_frequency_multiple_lines_same_doc_count_once(self):
        """Two lines on the same account within ONE document count as one
        distinct document (metric is COUNT(DISTINCT move_id), not lines)."""
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    Command.create(
                        {"account_id": self.exp2.id, "debit": 100.0, "credit": 0.0}
                    ),
                    Command.create(
                        {"account_id": self.exp2.id, "debit": 100.0, "credit": 0.0}
                    ),
                    Command.create(
                        {
                            "account_id": self.credit_account.id,
                            "debit": 0.0,
                            "credit": 200.0,
                        }
                    ),
                ],
            }
        )
        move.action_post()

        row = self._expense_row(self.exp2)
        self.assertIsNotNone(row)
        self.assertEqual(row["count"], 1)

    def test_expense_frequency_excludes_draft_and_non_expense(self):
        """Draft (unposted) usage is ignored, and non-expense accounts never
        appear in the ranking."""
        self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    Command.create(
                        {"account_id": self.exp3.id, "debit": 100.0, "credit": 0.0}
                    ),
                    Command.create(
                        {
                            "account_id": self.credit_account.id,
                            "debit": 0.0,
                            "credit": 100.0,
                        }
                    ),
                ],
            }
        )  # left in draft on purpose

        items = (
            self.Dashboard.with_user(self.maker).get_expense_frequency()["items"]
        )
        self.assertFalse(
            any(row["id"] == self.exp3.id for row in items),
            "draft usage must not be counted",
        )
        self.assertFalse(
            any(row["id"] == self.credit_account.id for row in items),
            "non-expense account must never appear",
        )

    def test_expense_frequency_limit_and_ordering(self):
        """Result respects the limit and is sorted by count descending."""
        self._post_expense(self.exp1)
        self._post_expense(self.exp1)
        self._post_expense(self.exp2)

        items = (
            self.Dashboard.with_user(self.maker).get_expense_frequency(limit=1)[
                "items"
            ]
        )
        self.assertLessEqual(len(items), 1)

        counts = [
            row["count"]
            for row in self.Dashboard.with_user(self.maker).get_expense_frequency()[
                "items"
            ]
        ]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_expense_frequency_fiscal_year_filter(self):
        """The fiscal_year_id argument restricts the count to that period."""
        fy = self.env["account.fiscal.year"].create(
            {
                "name": "FY-TEST-2020",
                "date_from": "2020-01-01",
                "date_to": "2020-12-31",
                "company_id": self.company.id,
            }
        )
        self._post_expense(self.exp1, date="2020-06-01")  # inside the FY
        self._post_expense(self.exp1)  # today -> outside the FY

        row = self._expense_row(self.exp1, fiscal_year_id=fy.id)
        self.assertIsNotNone(row)
        self.assertEqual(row["count"], 1)

    def test_analytics_aging_ap_bucket(self):
        """An overdue payable lands in the correct aging bucket (delta is
        isolated from any pre-existing data)."""
        before = self._analytics()["aging"]["ap"]
        self._post_invoice(
            "in_invoice",
            self.vendor_a,
            111.0,
            fields.Date.today() - timedelta(days=45),  # 31-60 bucket
        )
        after = self._analytics()["aging"]["ap"]
        self.assertAlmostEqual(after[2] - before[2], 111.0, places=2)

    def test_analytics_forecast_bucket(self):
        """A payable due within a week lands in the 0-7 forecast bucket."""
        before = self._analytics()["forecast"]
        self._post_invoice(
            "in_invoice",
            self.vendor_a,
            222.0,
            fields.Date.today() + timedelta(days=5),  # 0-7 bucket
        )
        after = self._analytics()["forecast"]
        self.assertAlmostEqual(after[1] - before[1], 222.0, places=2)

    def test_analytics_top_vendors_sorted_by_amount(self):
        """Vendors are ranked by outstanding payable, largest first."""
        self._post_invoice(
            "in_invoice", self.vendor_a, 999999.0, fields.Date.today()
        )
        self._post_invoice(
            "in_invoice", self.vendor_b, 888888.0, fields.Date.today()
        )

        top = self._analytics()["top_vendors"]
        self.assertLessEqual(len(top), 10)
        ids = [row["id"] for row in top]
        self.assertIn(self.vendor_a.id, ids)
        self.assertIn(self.vendor_b.id, ids)
        self.assertLess(
            ids.index(self.vendor_a.id),
            ids.index(self.vendor_b.id),
            "the larger balance must rank first",
        )
        row_a = next(row for row in top if row["id"] == self.vendor_a.id)
        self.assertAlmostEqual(row_a["amount"], 999999.0, places=2)
