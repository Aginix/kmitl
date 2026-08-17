from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProcurementPlanAnalytic(TransactionCase):
    """Test that analytic_distribution correctly populates convenience fields
    on procurement.plan when each dimension account is included."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # Analytic plans
        cls.plan_activities = env.ref(
            "account_analytic_kmitl.analytic_plan_activities"
        )
        cls.plan_departments = env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        cls.plan_funds = env.ref("account_analytic_kmitl.analytic_plan_funds")
        cls.plan_sources = env.ref("account_analytic_kmitl.analytic_plan_sources")

        # Create one analytic account per dimension for testing
        cls.activity_account = env["account.analytic.account"].create(
            {"name": "Test Activity", "plan_id": cls.plan_activities.id}
        )
        cls.department_account = env["account.analytic.account"].create(
            {"name": "Test Department", "plan_id": cls.plan_departments.id}
        )
        cls.fund_account = env["account.analytic.account"].create(
            {"name": "Test Fund", "plan_id": cls.plan_funds.id}
        )
        cls.source_account = env["account.analytic.account"].create(
            {"name": "Test Source", "plan_id": cls.plan_sources.id}
        )

        # Minimal required records
        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            from datetime import date

            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "2568",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                }
            )

    def _make_plan(self, analytic_distribution):
        """Helper: create a procurement.plan with the given analytic_distribution."""
        return self.env["procurement.plan"].create(
            {
                "description": "Test Plan",
                "amount": 1,
                "unit": "ชุด",
                "account_fiscal_year_id": self.fiscal_year.id,
                "analytic_distribution": analytic_distribution,
            }
        )

    def test_activity_analytic_id_computed_from_distribution(self):
        """activity_analytic_id must be set when activities account is in analytic_distribution."""
        plan = self._make_plan(
            {str(self.activity_account.id): 100}
        )
        self.assertEqual(
            plan.activity_analytic_id,
            self.activity_account,
            "activity_analytic_id should reflect the activities account in analytic_distribution",
        )

    def test_department_analytic_id_computed_from_distribution(self):
        """department_analytic_id must be set when departments account is in analytic_distribution."""
        plan = self._make_plan(
            {str(self.department_account.id): 100}
        )
        self.assertEqual(
            plan.department_analytic_id,
            self.department_account,
            "department_analytic_id should reflect the departments account in analytic_distribution",
        )

    def test_fund_analytic_id_computed_from_distribution(self):
        """fund_analytic_id must be set when funds account is in analytic_distribution."""
        plan = self._make_plan(
            {str(self.fund_account.id): 100}
        )
        self.assertEqual(
            plan.fund_analytic_id,
            self.fund_account,
            "fund_analytic_id should reflect the funds account in analytic_distribution",
        )

    def test_source_analytic_id_computed_from_distribution(self):
        """source_analytic_id must be set when sources account is in analytic_distribution."""
        plan = self._make_plan(
            {str(self.source_account.id): 100}
        )
        self.assertEqual(
            plan.source_analytic_id,
            self.source_account,
            "source_analytic_id should reflect the sources account in analytic_distribution",
        )

    def test_all_dimensions_computed_from_distribution(self):
        """All four convenience fields must be set simultaneously from analytic_distribution."""
        plan = self._make_plan(
            {
                str(self.activity_account.id): 100,
                str(self.department_account.id): 100,
                str(self.fund_account.id): 100,
                str(self.source_account.id): 100,
            }
        )
        self.assertEqual(plan.activity_analytic_id, self.activity_account)
        self.assertEqual(plan.department_analytic_id, self.department_account)
        self.assertEqual(plan.fund_analytic_id, self.fund_account)
        self.assertEqual(plan.source_analytic_id, self.source_account)

    def test_fields_empty_when_dimension_absent_from_distribution(self):
        """Convenience fields for dimensions not in analytic_distribution must remain empty."""
        plan = self._make_plan(
            {str(self.source_account.id): 100}
        )
        self.assertFalse(plan.activity_analytic_id)
        self.assertFalse(plan.department_analytic_id)
        self.assertFalse(plan.fund_analytic_id)
        self.assertEqual(plan.source_analytic_id, self.source_account)

    def test_fields_updated_when_distribution_changes(self):
        """Changing analytic_distribution on an existing plan must recompute the fields."""
        plan = self._make_plan(
            {str(self.source_account.id): 100}
        )
        self.assertFalse(plan.activity_analytic_id)

        plan.analytic_distribution = {
            str(self.source_account.id): 100,
            str(self.activity_account.id): 100,
        }
        self.assertEqual(plan.activity_analytic_id, self.activity_account)
