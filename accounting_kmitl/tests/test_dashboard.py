# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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

    def test_structure_and_domain_self_consistency(self):
        """Every card exposes count + domain, and the count equals a fresh
        search_count over that same domain (money cards also expose amount)."""
        Move = self.env["account.move"].with_user(self.maker)
        data = self.Dashboard.with_user(self.maker).get_dashboard_data()

        self.assertIn("currency_symbol", data)
        self.assertEqual(set(data["cards"]), CARD_KEYS)

        for key, card in data["cards"].items():
            self.assertIn("domain", card, key)
            self.assertEqual(
                card["count"], Move.search_count(card["domain"]), key
            )
            if key in MONEY_CARDS:
                self.assertIn("amount", card, key)
            else:
                self.assertNotIn("amount", card, key)

        # overdue_ap must be the unpaid_ap domain further narrowed by due date.
        overdue = data["cards"]["overdue_ap"]["domain"]
        self.assertTrue(
            any(term[0] == "invoice_date_due" for term in overdue),
            "overdue_ap domain must filter on invoice_date_due",
        )

    def test_my_drafts_scoped_to_current_user(self):
        """my_drafts counts only the caller's own draft documents."""
        before = self.Dashboard.with_user(self.maker).get_dashboard_data()
        base = before["cards"]["my_drafts"]["count"]

        self._entry(self.maker, self._balanced_lines())
        self._entry(self.other, self._balanced_lines())  # not the caller's

        after = self.Dashboard.with_user(self.maker).get_dashboard_data()
        self.assertEqual(after["cards"]["my_drafts"]["count"], base + 1)

    def test_submitted_card(self):
        """A clean entry submits successfully and shows on the submitted card."""
        move = self._entry(self.maker, self._balanced_lines())
        move.with_user(self.maker).action_submit()
        self.assertEqual(move.state, "submitted")

        data = self.Dashboard.with_user(self.maker).get_dashboard_data()
        self.assertGreaterEqual(data["cards"]["submitted"]["count"], 1)

    def test_exception_card(self):
        """Submitting a self-canceling pair is halted (popup) but flags the
        move with an exception, so the exceptions card picks it up."""
        move = self._entry(self.maker, self._self_canceling_lines())
        move.with_user(self.maker).action_submit()  # returns a popup action
        self.assertTrue(move.exception_ids)
        self.assertEqual(move.state, "draft")

        data = self.Dashboard.with_user(self.maker).get_dashboard_data()
        self.assertGreaterEqual(data["cards"]["exceptions"]["count"], 1)
