# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetCapDraft(TransactionCase):
    """`_check_amount_within_commitment` on พจ.1 (PA) at `draft`.

    - Related field `budget_commitment_amount` surfaces the commitment cap.
    - Aggregate PA total > commitment amount raises `ValidationError`.
    - Boundary equal-to-cap is allowed.
    - Shared-commitment (KMITL Project) case aggregates across sibling PAs.
    - PA without commitment is untouched by the rail.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")

        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-TEST-PA-BUDCAP",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": env.company.id,
                }
            )

        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTPACAP001",
                "name": "Test PA Budget-Cap Draft",
                "budget_type": "expense",
                "budgetable": True,
            }
        )

        cls.commitment = env["budget.commitment"].create(
            {
                "amount": 100_000.0,
                "account_id": cls.budget_account.id,
                "account_fiscal_year_id": cls.fiscal_year.id,
            }
        )

    def _make_pa(self, unit_price=100.0, qty=10.0, commitment=True):
        pr = self.env["purchase.request"].create(
            {
                "title": "Test PR",
                "requested_by": self.env.ref("base.user_admin").id,
                "account_fiscal_year_id": self.fiscal_year.id,
            }
        )
        if commitment:
            pr.write({"budget_commitment_id": self.commitment.id})
        pa = self.env["purchase.request.approval"].create(
            {
                "request_id": pr.id,
                "title": "PA under test",
            }
        )
        self.env["purchase.request.approval.line"].create(
            {
                "approval_id": pa.id,
                "name": "Test line",
                "product_qty": qty,
                "price_unit": unit_price,
            }
        )
        return pa

    def test_display_field_shows_commitment_amount(self):
        pa = self._make_pa()
        self.assertEqual(pa.budget_commitment_amount, self.commitment.amount)

    def test_draft_overspend_raises(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0)
        with self.assertRaises(ValidationError) as cm:
            pa.line_ids.write({"price_unit": 20_000.0})
        self.assertIn("จำนวนเงินที่จองงบไว้", str(cm.exception))

    def test_draft_at_boundary_passes(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0)
        pa.line_ids.write({"price_unit": 10_000.0})
        self.assertEqual(pa.amount_total, self.commitment.amount)

    def test_shared_commitment_aggregate_raises(self):
        pa_a = self._make_pa(unit_price=4_000.0, qty=10.0)
        pa_b = self._make_pa(unit_price=4_000.0, qty=10.0)
        self.assertEqual(pa_a.budget_commitment_id, self.commitment)
        self.assertEqual(pa_b.budget_commitment_id, self.commitment)
        with self.assertRaises(ValidationError):
            pa_a.line_ids.write({"price_unit": 7_000.0})

    def test_no_commitment_no_check(self):
        pa = self._make_pa(unit_price=1_000.0, qty=10.0, commitment=False)
        pa.line_ids.write({"price_unit": 1_000_000.0})
        self.assertEqual(pa.amount_total, 10_000_000.0)
