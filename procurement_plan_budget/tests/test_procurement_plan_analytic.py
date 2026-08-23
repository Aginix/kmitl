from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProcurementPlanAnalytic(TransactionCase):
    """Test that analytic_distribution correctly populates convenience fields
    on procurement.plan when each dimension account is included.

    Lives in procurement_plan_budget (not core) because budget_account_id is
    required=True in this layer; all tests create procurement.plan records so
    the suite would fail on missing required field when the budget module is
    installed (which CI always does).  The assertions themselves exercise core
    analytic logic — the placement is purely to satisfy the required constraint.
    """

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

        cls.budget_account = env["budget.account"].search(
            [("procurement_plan", "=", True), ("budgetable", "=", True), ("budget_type", "=", "expense")],
            limit=1,
        )
        if not cls.budget_account:
            cls.budget_account = env["budget.account"].create(
                {
                    "name": "Test Procurement Budget Account",
                    "code": "TESTPROC",
                    "procurement_plan": True,
                    "budgetable": True,
                    "budget_type": "expense",
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
                "budget_account_id": self.budget_account.id,
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
