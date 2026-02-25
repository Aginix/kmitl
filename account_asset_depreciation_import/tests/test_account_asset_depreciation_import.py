# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api, fields, registry
from odoo.exceptions import ValidationError
from odoo.tests import get_db_name, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountAssetDepreciationImport(AccountTestInvoicingCommon):
    """Tests for already_depreciated_amount_import on account.asset.

    Scenario baseline:
      - purchase_value = 60,000  salvage_value = 0
      - linear, 5 years, period = year
      - depreciation_base = 60,000  →  12,000/year
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        with registry(get_db_name()).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if not env.ref("l10n_generic_coa.configurable_chart_template", False):
                coa = env["account.chart.template"].search([("visible", "=", True)])[:1]
                chart_template_ref = coa.get_external_id()[coa.id]
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.asset_model = cls.env["account.asset"]
        cls.profile = cls.env["account.asset.profile"].create(
            {
                "account_expense_depreciation_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": cls.company_data["default_account_assets"].id,
                "account_depreciation_id": cls.company_data[
                    "default_account_assets"
                ].id,
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "name": "Test Profile - 5 Years Linear",
                "method_time": "year",
                "method_number": 5,
                "method_period": "year",
            }
        )

    def _make_asset(self, purchase_value=60000.0, import_amount=0.0, **kw):
        """Helper: create a draft 5-year linear asset."""
        vals = {
            "name": "Test Asset",
            "profile_id": self.profile.id,
            "purchase_value": purchase_value,
            "salvage_value": 0.0,
            "already_depreciated_amount_import": import_amount,
            "date_start": "2020-01-01",
            "method_time": "year",
            "method_number": 5,
            "method_period": "year",
        }
        vals.update(kw)
        return self.asset_model.create(vals)

    # ------------------------------------------------------------------ #
    # Constraint tests                                                     #
    # ------------------------------------------------------------------ #

    def test_constraint_negative_import(self):
        """Import amount must not be negative."""
        asset = self._make_asset()
        with self.assertRaises(ValidationError):
            asset.already_depreciated_amount_import = -1.0
            asset._check_already_depreciated_amount_import()

    def test_constraint_exceeds_base(self):
        """Import amount must not exceed depreciation_base."""
        asset = self._make_asset(purchase_value=60000.0)
        with self.assertRaises(ValidationError):
            asset.already_depreciated_amount_import = 60001.0
            asset._check_already_depreciated_amount_import()

    def test_constraint_equal_base_is_ok(self):
        """Import amount equal to depreciation_base is valid."""
        asset = self._make_asset(import_amount=60000.0)
        # Should not raise
        asset._check_already_depreciated_amount_import()

    # ------------------------------------------------------------------ #
    # _compute_depreciation: value_residual / value_depreciated           #
    # ------------------------------------------------------------------ #

    def test_compute_depreciation_no_import(self):
        """Without import, residual = depreciation_base (no lines posted)."""
        asset = self._make_asset()
        asset.invalidate_recordset()
        self.assertAlmostEqual(asset.value_residual, 60000.0)
        self.assertAlmostEqual(asset.value_depreciated, 0.0)

    def test_compute_depreciation_with_import(self):
        """Import reduces residual immediately, before any board computation."""
        asset = self._make_asset(import_amount=24000.0)
        asset.invalidate_recordset()
        self.assertAlmostEqual(asset.value_residual, 36000.0)
        self.assertAlmostEqual(asset.value_depreciated, 24000.0)

    def test_compute_depreciation_full_import(self):
        """Full import → residual = 0, depreciated = full base."""
        asset = self._make_asset(import_amount=60000.0)
        asset.invalidate_recordset()
        self.assertAlmostEqual(asset.value_residual, 0.0)
        self.assertAlmostEqual(asset.value_depreciated, 60000.0)

    # ------------------------------------------------------------------ #
    # compute_depreciation_board: no import (unchanged behaviour)         #
    # ------------------------------------------------------------------ #

    def test_board_no_import_line_count(self):
        """No import → 5 depreciation lines as normal."""
        asset = self._make_asset()
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(lambda l: l.type == "depreciate")
        # One purchase line + 5 depreciation lines
        self.assertEqual(len(dlines), 5)

    def test_board_no_import_amounts(self):
        """No import → each period = 12,000."""
        asset = self._make_asset()
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        for line in dlines:
            self.assertAlmostEqual(line.amount, 12000.0)

    # ------------------------------------------------------------------ #
    # compute_depreciation_board: with import                             #
    # ------------------------------------------------------------------ #

    def test_board_import_line_count(self):
        """24,000 import on 60,000/5yr asset → 3 depreciation lines (not 5)."""
        asset = self._make_asset(import_amount=24000.0)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(lambda l: l.type == "depreciate")
        self.assertEqual(len(dlines), 3)

    def test_board_import_amounts_unchanged(self):
        """Per-period rate stays at 12,000 even with import."""
        asset = self._make_asset(import_amount=24000.0)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        for line in dlines:
            self.assertAlmostEqual(line.amount, 12000.0)

    def test_board_import_first_line_depreciated_value(self):
        """First line's depreciated_value should equal the import amount."""
        asset = self._make_asset(import_amount=24000.0)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        self.assertAlmostEqual(dlines[0].depreciated_value, 24000.0)

    def test_board_import_last_line_remaining_value(self):
        """Last line's remaining_value should be 0 (fully depreciated)."""
        asset = self._make_asset(import_amount=24000.0)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        self.assertAlmostEqual(dlines[-1].remaining_value, 0.0)

    def test_board_import_cumulative_depreciated_values(self):
        """Cumulative depreciated_value on each line is correct."""
        asset = self._make_asset(import_amount=24000.0)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        expected_depreciated = [24000.0, 36000.0, 48000.0]
        for line, expected in zip(dlines, expected_depreciated):
            self.assertAlmostEqual(line.depreciated_value, expected)

    def test_board_import_cumulative_remaining_values(self):
        """Cumulative remaining_value on each line is correct."""
        asset = self._make_asset(import_amount=24000.0)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        expected_remaining = [24000.0, 12000.0, 0.0]
        for line, expected in zip(dlines, expected_remaining):
            self.assertAlmostEqual(line.remaining_value, expected)

    # ------------------------------------------------------------------ #
    # Edge cases                                                           #
    # ------------------------------------------------------------------ #

    def test_board_full_import_no_lines(self):
        """Full import (= depreciation_base) → no depreciation lines generated."""
        asset = self._make_asset(import_amount=60000.0)
        # value_residual = 0, so compute_depreciation_board skips the asset
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(lambda l: l.type == "depreciate")
        self.assertEqual(len(dlines), 0)

    def test_board_import_one_period_left(self):
        """48,000 import on 60,000/5yr → exactly 1 remaining line of 12,000."""
        asset = self._make_asset(import_amount=48000.0)
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(lambda l: l.type == "depreciate")
        self.assertEqual(len(dlines), 1)
        self.assertAlmostEqual(dlines[0].amount, 12000.0)
        self.assertAlmostEqual(dlines[0].depreciated_value, 48000.0)
        self.assertAlmostEqual(dlines[0].remaining_value, 0.0)

    def test_board_zero_import_is_normal(self):
        """Zero import delegates to super and behaves identically to no-import case."""
        asset_no_import = self._make_asset(import_amount=0.0)
        asset_no_import.compute_depreciation_board()
        asset_no_import.invalidate_recordset()

        asset_zero = self._make_asset(import_amount=0.0)
        asset_zero.compute_depreciation_board()
        asset_zero.invalidate_recordset()

        dlines_no = asset_no_import.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        dlines_zero = asset_zero.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")

        self.assertEqual(len(dlines_no), len(dlines_zero))
        for l1, l2 in zip(dlines_no, dlines_zero):
            self.assertAlmostEqual(l1.amount, l2.amount)
            self.assertAlmostEqual(l1.depreciated_value, l2.depreciated_value)
            self.assertAlmostEqual(l1.remaining_value, l2.remaining_value)

    # ------------------------------------------------------------------ #
    # Degressive method                                                    #
    # ------------------------------------------------------------------ #

    def test_board_degressive_with_import(self):
        """Degressive method: import reduces residual; rate applied to reduced base."""
        profile_degr = self.env["account.asset.profile"].create(
            {
                "account_expense_depreciation_id": self.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "journal_id": self.company_data["default_journal_purchase"].id,
                "name": "Degressive 5 Years",
                "method": "degressive",
                "method_time": "year",
                "method_number": 5,
                "method_period": "year",
                "method_progress_factor": 0.40,
            }
        )
        asset = self.asset_model.create(
            {
                "name": "Degressive Asset",
                "profile_id": profile_degr.id,
                "purchase_value": 100000.0,
                "salvage_value": 0.0,
                "already_depreciated_amount_import": 40000.0,
                "date_start": "2020-01-01",
                "method": "degressive",
                "method_time": "year",
                "method_number": 5,
                "method_period": "year",
                "method_progress_factor": 0.40,
            }
        )
        asset.invalidate_recordset()
        # value_residual = 100,000 - 40,000 = 60,000
        self.assertAlmostEqual(asset.value_residual, 60000.0)

        asset.compute_depreciation_board()
        asset.invalidate_recordset()

        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        self.assertTrue(len(dlines) > 0)

        # First period: 40% of 60,000 = 24,000
        self.assertAlmostEqual(dlines[0].amount, 24000.0)
        self.assertAlmostEqual(dlines[0].depreciated_value, 40000.0)

        # Last line must exhaust remaining value (remaining_value = 0)
        self.assertAlmostEqual(dlines[-1].remaining_value, 0.0)

    # ------------------------------------------------------------------ #
    # Monthly period                                                       #
    # ------------------------------------------------------------------ #

    def test_board_monthly_import_line_count(self):
        """Monthly period: 24,000 import on 60,000/5yr → 36 months (not 60)."""
        asset = self._make_asset(
            import_amount=24000.0,
            method_period="month",
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(lambda l: l.type == "depreciate")
        self.assertEqual(len(dlines), 36)

    def test_board_monthly_import_per_period_amount(self):
        """Monthly: per-period = 12,000/12 = 1,000 (same rate as no-import)."""
        asset = self._make_asset(
            import_amount=24000.0,
            method_period="month",
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        # All interior lines should be 1,000; only last may differ by rounding
        for line in dlines[:-1]:
            self.assertAlmostEqual(line.amount, 1000.0)
        # Last line cleans up any rounding to reach 0 remaining
        self.assertAlmostEqual(dlines[-1].remaining_value, 0.0)

    # ------------------------------------------------------------------ #
    # No negative remaining_value (regression)                             #
    # ------------------------------------------------------------------ #

    def test_board_no_negative_remaining_value(self):
        """Remaining value must never go negative on any depreciation line."""
        asset = self._make_asset(
            purchase_value=1500.0,
            import_amount=100.0,
            salvage_value=1.0,
            date_start="2026-02-25",
            method_number=3,
            method_period="month",
        )
        asset.compute_depreciation_board()
        asset.invalidate_recordset()
        dlines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate"
        ).sorted("line_date")
        self.assertTrue(len(dlines) > 0)
        for line in dlines:
            self.assertGreaterEqual(
                line.remaining_value,
                0.0,
                f"Negative remaining_value {line.remaining_value} on {line.line_date}",
            )
            self.assertGreaterEqual(
                line.amount,
                0.0,
                f"Negative amount {line.amount} on {line.line_date}",
            )
        self.assertAlmostEqual(dlines[-1].remaining_value, 0.0)
        self.assertAlmostEqual(dlines[0].depreciated_value, 100.0)
