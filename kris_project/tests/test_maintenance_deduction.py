from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMaintenanceDeduction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env["kris.project"]
        cls.category = cls.env["kris.project.category"].create(
            {"name": "Test Category"}
        )
        cls.project_type = cls.env["kris.project.type"].create(
            {"name": "Test Type", "category_id": cls.category.id}
        )

    def _make_project(self, **vals):
        base = {
            "project_name": "Test Project",
            "project_category_id": self.category.id,
            "project_type_id": self.project_type.id,
        }
        base.update(vals)
        return self.Project.create(base)

    def test_tiered_deduction(self):
        # operating_expense = 2,000,000 -> 1M * 10% + 1M * 9% = 190,000
        project = self._make_project(
            project_value=2_000_000.0,
            maintenance_deduction_type="tiered",
        )
        self.assertAlmostEqual(
            project.maintenance_deduction_amount, 190_000.0, places=2
        )

    def test_custom_percentage_deduction(self):
        # operating_expense = 2,000,000 * 5% = 100,000
        project = self._make_project(
            project_value=2_000_000.0,
            maintenance_deduction_type="custom",
            maintenance_deduction_pct=5.0,
        )
        self.assertAlmostEqual(
            project.maintenance_deduction_amount, 100_000.0, places=2
        )

    def test_fixed_amount_deduction(self):
        # The entered figure is used verbatim, independent of operating_expense.
        project = self._make_project(
            project_value=2_000_000.0,
            maintenance_deduction_type="fixed",
            maintenance_deduction_fixed_amount=123_456.0,
        )
        self.assertAlmostEqual(
            project.maintenance_deduction_amount, 123_456.0, places=2
        )

    def test_fixed_amount_recomputes_on_change(self):
        project = self._make_project(
            project_value=2_000_000.0,
            maintenance_deduction_type="fixed",
            maintenance_deduction_fixed_amount=50_000.0,
        )
        project.maintenance_deduction_fixed_amount = 75_000.0
        self.assertAlmostEqual(
            project.maintenance_deduction_amount, 75_000.0, places=2
        )

    def test_warn_fixed_exceeds_expense(self):
        project = self._make_project(
            project_value=100_000.0,
            maintenance_deduction_type="fixed",
            maintenance_deduction_fixed_amount=150_000.0,
        )
        self.assertTrue(project.warn_maintenance_exceeds_expense)

    def test_no_warn_fixed_within_expense(self):
        project = self._make_project(
            project_value=100_000.0,
            maintenance_deduction_type="fixed",
            maintenance_deduction_fixed_amount=50_000.0,
        )
        self.assertFalse(project.warn_maintenance_exceeds_expense)

    def test_warn_is_method_agnostic_custom_over_100(self):
        # A custom percentage above 100% also trips the warning.
        project = self._make_project(
            project_value=100_000.0,
            maintenance_deduction_type="custom",
            maintenance_deduction_pct=150.0,
        )
        self.assertTrue(project.warn_maintenance_exceeds_expense)

    def test_switching_type_clears_inactive_inputs(self):
        # Switching the method clears the input that no longer applies, so no
        # stale value lingers in storage or on export.
        form = Form(self.Project)
        form.project_name = "Switch Test"
        form.project_category_id = self.category
        form.project_type_id = self.project_type
        form.project_value = 2_000_000.0

        form.maintenance_deduction_type = "fixed"
        form.maintenance_deduction_fixed_amount = 123_456.0

        form.maintenance_deduction_type = "custom"
        self.assertEqual(form.maintenance_deduction_fixed_amount, 0.0)

        form.maintenance_deduction_pct = 5.0
        form.maintenance_deduction_type = "fixed"
        self.assertEqual(form.maintenance_deduction_pct, 0.0)
