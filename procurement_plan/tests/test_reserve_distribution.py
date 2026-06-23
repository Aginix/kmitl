from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReserveDistribution(TransactionCase):
    """The plan's reservation commitment must carry the plan's own
    procurement_plan analytic dimension (the ownership tag) in
    analytic_distribution, so the reserve line stays attributable to the plan
    (see budget.controller _POOL_TAG_COLUMNS)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        # No appropriation is set up here; allow the reserve without availability.
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")

        cls.activity_account = env["account.analytic.account"].create(
            {
                "name": "Test Activity",
                "plan_id": env.ref(
                    "account_analytic_kmitl.analytic_plan_activities"
                ).id,
            }
        )
        cls.department_account = env["account.analytic.account"].create(
            {
                "name": "Test Department",
                "plan_id": env.ref(
                    "account_analytic_kmitl.analytic_plan_departments"
                ).id,
            }
        )
        cls.fund_account = env["account.analytic.account"].create(
            {
                "name": "Test Fund",
                "plan_id": env.ref("account_analytic_kmitl.analytic_plan_funds").id,
            }
        )
        cls.source_account = env["account.analytic.account"].create(
            {
                "name": "Test Source",
                "plan_id": env.ref(
                    "account_analytic_kmitl.analytic_plan_sources"
                ).id,
            }
        )

        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-TEST",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": env.company.id,
                }
            )

        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTPPRES",
                "name": "Test Procurement Plan Code",
                "budget_type": "expense",
                "budgetable": True,
            }
        )

    def _financial_dims(self):
        return {
            str(self.activity_account.id): 100,
            str(self.department_account.id): 100,
            str(self.fund_account.id): 100,
            str(self.source_account.id): 100,
        }

    def _make_new_plan(self):
        """Create a plan and confirm it (draft->new): action_new mints the plan's
        own analytic account and folds it into analytic_distribution."""
        plan = self.env["procurement.plan"].create(
            {
                "description": "Test Plan",
                "amount": 1,
                "unit": "ชุด",
                "total_price": 1000.0,
                "account_fiscal_year_id": self.fiscal_year.id,
                "budget_account_id": self.budget_account.id,
                "purchase_request_eta": "1",
                "procurement_announcement_eta": "2",
                "approval_signing_eta": "3",
                "contract_order_signing_eta": "4",
                "acceptance_eta": "5",
                "analytic_distribution": self._financial_dims(),
            }
        )
        plan.action_new()
        return plan

    def _reserve_line(self, plan):
        commitment = plan.budget_commitment_ids.filtered(
            lambda c: c.state != "cancel"
        )[:1]
        self.assertTrue(commitment, "a reservation commitment should exist")
        return commitment.line_ids.filtered(
            lambda l: l.move_type == "reserve"
        )[:1]

    def test_reservation_carries_procurement_plan_tag(self):
        """After reserve, the reserve line carries the plan's own procurement_plan
        dimension plus the four financial dimensions."""
        plan = self._make_new_plan()
        self.assertTrue(
            plan.analytic_account_id,
            "action_new should mint the plan's own analytic account",
        )
        plan.action_ready()

        dist = self._reserve_line(plan).analytic_distribution or {}
        self.assertIn(
            str(plan.analytic_account_id.id),
            dist,
            "reserve line must carry the plan's own procurement_plan dimension",
        )
        for account in (
            self.activity_account,
            self.department_account,
            self.fund_account,
            self.source_account,
        ):
            self.assertIn(str(account.id), dist)

    def test_refold_restores_dropped_tag(self):
        """If analytic_distribution loses the procurement_plan dimension between
        action_new and reserve (e.g. a wholesale rewrite by a picker), the
        reserve step refolds it so the reserve line still carries the tag."""
        plan = self._make_new_plan()
        own_account = plan.analytic_account_id
        self.assertTrue(own_account)

        # Simulate a wholesale rewrite that drops the plan's own dimension.
        plan.analytic_distribution = self._financial_dims()
        self.assertNotIn(str(own_account.id), plan.analytic_distribution)

        plan.action_ready()

        self.assertIn(
            str(own_account.id),
            self._reserve_line(plan).analytic_distribution or {},
            "the reserve step must refold the dropped procurement_plan dimension",
        )
