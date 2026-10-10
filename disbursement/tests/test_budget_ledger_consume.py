# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import tagged

from odoo.addons.budget.tests.test_budget_ledger import BudgetLedgerCommon


@tagged("post_install", "-at_install")
class TestDisbursementLedgerConsume(BudgetLedgerCommon):
    """A disbursement request consumes its reservation with one consume event
    and no obligation (budget ADR-0016); undoing it restores the reservation
    exactly."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Ledger Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Ledger Service",
                "type": "service",
                "taxes_id": [(5, 0, 0)],
                "supplier_taxes_id": [(5, 0, 0)],
            }
        )

    def _request(self, commitment, amount):
        dr = self.env["disbursement.request"].create(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "line",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "partner_id": self.partner.id,
                        },
                    )
                ],
            }
        )
        dr.budget_commitment_id = commitment
        self.assertEqual(dr.amount_total, amount)
        return dr

    def test_approve_posts_one_consume_and_cancel_restores(self):
        self._appropriate(100_000)
        commitment = self._reserve(100_000)
        first = self._request(commitment, 30_000)
        second = self._request(commitment, 45_000)

        first._action_approve_budget()
        events = commitment._budget_event_lines(source=first)
        self.assertEqual(events.mapped("move_type"), ["consume"])
        self.assertEqual(events.budget_move_id.move_type, "consume")
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -70_000, "obligate": 0.0, "consume": -30_000},
        )
        # re-approving after a return to verification never double-cuts
        first._action_approve_budget()
        self.assertEqual(commitment.total_consumed, 30_000)

        second._action_approve_budget()
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -25_000, "obligate": 0.0, "consume": -75_000},
        )
        self.assertEqual(commitment.available_to_obligate, 25_000)
        self.assertEqual(commitment.state, "partial")
        # consumption was already reserved: the pool does not move
        self.assertEqual(self._available(), 0.0)

        # undoing one request gives back exactly its amount, the other stays
        first._reverse_own_commitment_lines(commitment)
        self.assertEqual(
            self._buckets(commitment),
            {"reserve": -55_000, "obligate": 0.0, "consume": -45_000},
        )
        self.assertFalse(commitment._has_budget_event(first, "consume"))
        self.assertTrue(commitment._has_budget_event(second, "consume"))
        self.assertEqual(self._available(), 0.0)
