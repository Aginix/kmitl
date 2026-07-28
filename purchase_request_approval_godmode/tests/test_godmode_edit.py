# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


GODMODE_GROUP = "purchase_request_approval_godmode.group_pa_godmode"
PA_MANAGER_GROUP = "purchase_request.group_purchase_request_manager"


@tagged("post_install", "-at_install")
class TestGodmodeEdit(TransactionCase):
    """God-Mode post-approval edits on พจ.1 (PA):

    - `user_has_godmode` compute reflects the current user's group membership.
    - `_check_godmode_amount_within_commitment` fires only in the (approved
      state) x (writer holds god-mode group) intersection.
    - Aggregate total of all approved PAs on the same budget commitment must
      not exceed the commitment's cap — covering both single-PA and
      KMITL-Project shared-commitment scenarios.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")

        cls.god_user = env["res.users"].create(
            {
                "name": "God User",
                "login": "god_pa",
                "email": "god_pa@example.com",
                "groups_id": [
                    (
                        4,
                        env.ref(PA_MANAGER_GROUP).id,
                    ),
                    (4, env.ref(GODMODE_GROUP).id),
                ],
            }
        )
        cls.plain_user = env["res.users"].create(
            {
                "name": "Plain User",
                "login": "plain_pa",
                "email": "plain_pa@example.com",
                "groups_id": [(4, env.ref(PA_MANAGER_GROUP).id)],
            }
        )

        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-TEST-GODMODE",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": env.company.id,
                }
            )

        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTGOD001",
                "name": "Test God Mode Code",
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

    def _make_pa(self, unit_price=100.0, qty=1.0):
        """Build a PR + PA in `approved` state whose PA line totals up to
        ``qty * unit_price``. The commitment linkage is done directly on the
        PR so no full budget-reservation workflow is needed.
        """
        pr = self.env["purchase.request"].create(
            {
                "title": "Test PR",
                "requested_by": self.env.ref("base.user_admin").id,
                "account_fiscal_year_id": self.fiscal_year.id,
            }
        )
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
        pa.write({"state": "approved"})
        return pa

    # ------------------------------------------------------------------
    #  user_has_godmode compute
    # ------------------------------------------------------------------

    def test_user_has_godmode_true_for_group_member(self):
        pa = self._make_pa()
        self.assertTrue(pa.with_user(self.god_user).user_has_godmode)

    def test_user_has_godmode_false_for_non_member(self):
        pa = self._make_pa()
        self.assertFalse(pa.with_user(self.plain_user).user_has_godmode)

    # ------------------------------------------------------------------
    #  Constraint — happy path
    # ------------------------------------------------------------------

    def test_godmode_edit_within_cap_passes(self):
        """God-mode user raises unit price but stays under the 100k cap."""
        pa = self._make_pa(unit_price=100.0, qty=10.0)  # total = 1_000
        pa.line_ids.with_user(self.god_user).write({"price_unit": 500.0})
        self.assertEqual(pa.amount_total, 5_000.0)

    # ------------------------------------------------------------------
    #  Constraint — over-cap raise
    # ------------------------------------------------------------------

    def test_godmode_edit_exceeds_cap_raises(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0)
        with self.assertRaises(ValidationError) as cm:
            pa.line_ids.with_user(self.god_user).write({"price_unit": 20_000.0})
        self.assertIn("เกินวงเงินอนุมัติ", str(cm.exception))

    # ------------------------------------------------------------------
    #  Constraint — skipped when not god-mode
    # ------------------------------------------------------------------

    def test_non_godmode_write_bypasses_constraint(self):
        """Per plan decision: the rail is a god-mode-specific check, so a
        non-god-mode writer is not caught by it. (The view is the real gate.)
        """
        pa = self._make_pa(unit_price=100.0, qty=10.0)
        pa.line_ids.with_user(self.plain_user).write({"price_unit": 20_000.0})
        # No ValidationError; total is now over cap but constraint didn't fire.
        self.assertGreater(pa.amount_total, self.commitment.amount)

    # ------------------------------------------------------------------
    #  Constraint — skipped in non-approved states
    # ------------------------------------------------------------------

    def test_constraint_skipped_in_draft(self):
        """Draft PA writes are governed by the base PR-reserve workflow, not
        by god-mode; the god-mode rail must not fire while state is draft.
        """
        pa = self._make_pa(unit_price=100.0, qty=10.0)
        pa.write({"state": "draft"})
        pa.line_ids.with_user(self.god_user).write({"price_unit": 20_000.0})
        self.assertEqual(pa.state, "draft")

    # ------------------------------------------------------------------
    #  Constraint — shared commitment (KMITL Project scenario)
    # ------------------------------------------------------------------

    def test_shared_commitment_two_pas(self):
        """PA-A + PA-B share one commitment (cap 100k). Given A=60k, B=30k,
        headroom is 10k. A god-mode edit that raises A by 20k must fail
        because the aggregate (80k + 30k) exceeds the shared cap.
        """
        pa_a = self._make_pa(unit_price=6_000.0, qty=10.0)  # 60_000
        pa_b = self._make_pa(unit_price=3_000.0, qty=10.0)  # 30_000
        # Both point at self.commitment via their PR.
        self.assertEqual(pa_a.budget_commitment_id, self.commitment)
        self.assertEqual(pa_b.budget_commitment_id, self.commitment)
        with self.assertRaises(ValidationError):
            pa_a.line_ids.with_user(self.god_user).write({"price_unit": 8_000.0})
