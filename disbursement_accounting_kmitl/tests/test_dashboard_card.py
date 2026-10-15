# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDisbursementDashboardCard(TransactionCase):
    def _cards_by_id(self, data):
        return {card["id"]: card for card in data["cards"]}

    def test_disbursement_card_added_alongside_base_cards(self):
        """The bridge appends its card without dropping the base cards, and the
        card is self-consistent (count == search_count over its domain)."""
        data = self.env["accounting.kmitl.dashboard"].get_dashboard_data()
        cards = self._cards_by_id(data)

        # base cards still present -> super() was chained
        self.assertIn("unpaid_ap", cards)

        card = cards.get("disbursement_awaiting_bill")
        self.assertIsNotNone(card, "disbursement card missing")
        self.assertEqual(card["res_model"], "disbursement.request")
        self.assertEqual(card["domain"], [("state", "=", "approved")])
        self.assertNotIn("amount", card)  # count-only card
        self.assertEqual(
            card["count"],
            self.env["disbursement.request"].search_count(card["domain"]),
        )
