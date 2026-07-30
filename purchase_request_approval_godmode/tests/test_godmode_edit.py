# -*- coding: utf-8 -*-
from datetime import date
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


GODMODE_GROUP = "purchase_request_approval_godmode.group_pa_godmode"
PA_MANAGER_GROUP = "purchase_request.group_purchase_request_manager"


@tagged("post_install", "-at_install")
class TestGodmodeEdit(TransactionCase):
    """God-Mode post-approval edits on พจ.1 (PA):

    - `user_has_godmode` compute reflects the current user's group membership.
    - `_check_godmode_amount_within_commitment` fires in `to_approve` and
      `approved` states, only for god-mode-group holders.
    - Aggregate total of PAs sharing a commitment must not exceed the cap
      — single-PA and shared-commitment scenarios.
    - God-Mode writes are silent (no chatter, no mail.thread tracking).
    - PDF attachment is regenerated when a PDF-visible field is edited.
    - Line `name` is editable under God-Mode.
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
                    (4, env.ref(PA_MANAGER_GROUP).id),
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

    def _make_pa(self, unit_price=100.0, qty=1.0, state="approved"):
        """Build a PR + PA whose PA line totals up to ``qty * unit_price``.
        The commitment linkage is set directly on the PR. PA is forced into
        ``state`` (default: ``approved``).
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
        pa.write({"state": state})
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

    def test_godmode_edit_within_cap_passes_in_approved(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        pa.line_ids.with_user(self.god_user).write({"price_unit": 500.0})
        self.assertEqual(pa.amount_total, 5_000.0)

    def test_godmode_edit_within_cap_passes_in_to_approve(self):
        """v2 scope extension: God-Mode also works in `to_approve`."""
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="to_approve")
        pa.line_ids.with_user(self.god_user).write({"price_unit": 500.0})
        self.assertEqual(pa.amount_total, 5_000.0)

    # ------------------------------------------------------------------
    #  Constraint — over-cap raise
    # ------------------------------------------------------------------

    def test_godmode_edit_exceeds_cap_raises_in_approved(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        with self.assertRaises(ValidationError) as cm:
            pa.line_ids.with_user(self.god_user).write({"price_unit": 20_000.0})
        self.assertIn("เกินวงเงินอนุมัติ", str(cm.exception))

    def test_godmode_edit_exceeds_cap_raises_in_to_approve(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="to_approve")
        with self.assertRaises(ValidationError):
            pa.line_ids.with_user(self.god_user).write({"price_unit": 20_000.0})

    # ------------------------------------------------------------------
    #  Constraint — skipped when not god-mode
    # ------------------------------------------------------------------

    def test_non_godmode_write_bypasses_constraint(self):
        """View-only rail — the model constraint is god-mode-specific."""
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        pa.line_ids.with_user(self.plain_user).write({"price_unit": 20_000.0})
        self.assertGreater(pa.amount_total, self.commitment.amount)

    # ------------------------------------------------------------------
    #  Constraint — skipped in states outside God-Mode scope
    # ------------------------------------------------------------------

    def test_constraint_skipped_in_draft(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        pa.write({"state": "draft"})
        pa.line_ids.with_user(self.god_user).write({"price_unit": 20_000.0})
        self.assertEqual(pa.state, "draft")

    # ------------------------------------------------------------------
    #  Line name is editable in God-Mode (v2 addition)
    # ------------------------------------------------------------------

    def test_line_name_editable_in_godmode(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        pa.line_ids.with_user(self.god_user).write({"name": "แก้ชื่อรายการโดย god-mode"})
        self.assertEqual(pa.line_ids.name, "แก้ชื่อรายการโดย god-mode")

    # ------------------------------------------------------------------
    #  Silent write — no chatter posted (v2 addition)
    # ------------------------------------------------------------------

    def test_write_silent_no_chatter(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        # Bypass PDF regen (which posts its own message via base
        # `report_generate`) so this test isolates the tracking-suppression
        # concern. See `test_pdf_regenerate_on_visible_edit` for the regen
        # happy path.
        with patch.object(
            type(pa), "_regenerate_report_pdf", lambda self: None
        ):
            before = len(pa.message_ids)
            pa.with_user(self.god_user).write(
                {"payment_type": "advance"}
            )
            after = len(pa.message_ids)
        self.assertEqual(before, after,
            "God-Mode edits must not post to chatter or fire tracking.")

    # ------------------------------------------------------------------
    #  PDF regen — triggered when a PDF-visible field is edited
    # ------------------------------------------------------------------

    def test_pdf_regenerate_on_visible_edit(self):
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        called = []
        with patch.object(
            type(pa),
            "_regenerate_report_pdf",
            lambda self: called.append(self.id),
        ):
            pa.with_user(self.god_user).write({"payment_type": "advance"})
        self.assertEqual(called, [pa.id],
            "PDF regen must run when a PDF-visible field is edited by god-mode.")

    def test_pdf_regen_not_triggered_for_non_pdf_field(self):
        """A write from god-mode to a non-PDF-visible field must not
        trigger PDF regen.
        """
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        called = []
        with patch.object(
            type(pa),
            "_regenerate_report_pdf",
            lambda self: called.append(self.id),
        ):
            # `origin` is a stored, editable, non-PDF-visible field.
            pa.with_user(self.god_user).write({"origin": "TEST-ORIGIN"})
        self.assertEqual(called, [],
            "PDF regen must not fire when the edited field is not in the PDF.")

    def test_pdf_regen_deletes_old_and_creates_new(self):
        """Verify the low-level regen logic: given a stored attachment,
        `_regenerate_report_pdf` unlinks it and calls `report_generate()`
        (which is then patched to a stub that just re-creates the
        attachment, isolating the delete-then-create sequence from
        QWeb rendering).
        """
        pa = self._make_pa(unit_price=100.0, qty=10.0, state="approved")
        pa.name = "PA-REGEN-001"
        attachment_name = pa.name + ".pdf"
        old = self.env["ir.attachment"].create(
            {
                "name": attachment_name,
                "res_model": pa._name,
                "res_id": pa.id,
                "datas": b"old",
            }
        )
        old_id = old.id

        def _stub_generate(self):
            self.env["ir.attachment"].create(
                {
                    "name": attachment_name,
                    "res_model": self._name,
                    "res_id": self.id,
                    "datas": b"new",
                }
            )

        with patch.object(type(pa), "report_generate", _stub_generate):
            pa._regenerate_report_pdf()

        self.assertFalse(
            self.env["ir.attachment"].browse(old_id).exists(),
            "Old attachment must be unlinked.",
        )
        fresh = self.env["ir.attachment"].search(
            [
                ("res_model", "=", pa._name),
                ("res_id", "=", pa.id),
                ("name", "=", attachment_name),
            ]
        )
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh.datas.decode(), "new")

    # ------------------------------------------------------------------
    #  Constraint — shared commitment (KMITL Project scenario)
    # ------------------------------------------------------------------

    def test_shared_commitment_two_pas(self):
        """PA-A + PA-B share one commitment (cap 100k). Given A=60k, B=30k,
        a god-mode edit that raises A by 20k must fail because the aggregate
        (80k + 30k) exceeds the shared cap.
        """
        pa_a = self._make_pa(unit_price=6_000.0, qty=10.0, state="approved")
        pa_b = self._make_pa(unit_price=3_000.0, qty=10.0, state="approved")
        self.assertEqual(pa_a.budget_commitment_id, self.commitment)
        self.assertEqual(pa_b.budget_commitment_id, self.commitment)
        with self.assertRaises(ValidationError):
            pa_a.line_ids.with_user(self.god_user).write({"price_unit": 8_000.0})
