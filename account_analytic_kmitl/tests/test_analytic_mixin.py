from odoo import api, fields, models
from odoo.tests.common import TransactionCase, tagged


class AnalyticMixinTestModel(models.TransientModel):
    """Transient model to test AnalyticMixin methods."""

    _name = "test.analytic.mixin"
    _description = "Test Analytic Mixin"
    _inherit = "analytic.mixin"

    name = fields.Char()

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
    )

    def _inverse_activity_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        for rec in self:
            rec._update_analytic_distribution("sources")


@tagged("post_install", "-at_install")
class TestAnalyticMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Register test model in the Odoo registry
        AnalyticMixinTestModel._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            ["test.analytic.mixin"],
            {"module": "account_analytic_kmitl"},
        )

        Plan = cls.env["account.analytic.plan"]
        Account = cls.env["account.analytic.account"]

        cls.plan_activities = Plan.search([("code", "=", "activities")], limit=1)
        cls.plan_departments = Plan.search([("code", "=", "departments")], limit=1)
        cls.plan_funds = Plan.search([("code", "=", "funds")], limit=1)
        cls.plan_sources = Plan.search([("code", "=", "sources")], limit=1)

        if not cls.plan_activities:
            cls.plan_activities = Plan.create(
                {"name": "Activities", "code": "activities"}
            )
        if not cls.plan_departments:
            cls.plan_departments = Plan.create(
                {"name": "Departments", "code": "departments"}
            )
        if not cls.plan_funds:
            cls.plan_funds = Plan.create({"name": "Funds", "code": "funds"})
        if not cls.plan_sources:
            cls.plan_sources = Plan.create({"name": "Sources", "code": "sources"})

        cls.activity_acc = Account.create(
            {
                "name": "Test Activity",
                "code": "TEST_ACT",
                "plan_id": cls.plan_activities.id,
            }
        )
        cls.department_acc = Account.create(
            {
                "name": "Test Department",
                "code": "TEST_DEP",
                "plan_id": cls.plan_departments.id,
            }
        )
        cls.fund_acc = Account.create(
            {
                "name": "Test Fund",
                "code": "TEST_FND",
                "plan_id": cls.plan_funds.id,
            }
        )
        cls.source_acc = Account.create(
            {
                "name": "Test Source",
                "code": "TEST_SRC",
                "plan_id": cls.plan_sources.id,
            }
        )

        cls.Model = cls.env["test.analytic.mixin"]

    def _create_record(self, distribution=None):
        vals = {"name": "Test"}
        if distribution:
            vals["analytic_distribution"] = distribution
        return self.Model.create(vals)

    # ------------------------------------------------------------------
    # Compute: analytic_distribution → dimension fields
    # ------------------------------------------------------------------

    def test_compute_single_dimension(self):
        """Setting analytic_distribution with one account populates the
        corresponding dimension field."""
        rec = self._create_record({str(self.activity_acc.id): 100})
        self.assertEqual(rec.activity_analytic_id, self.activity_acc)
        self.assertFalse(rec.department_analytic_id)
        self.assertFalse(rec.fund_analytic_id)
        self.assertFalse(rec.source_analytic_id)

    def test_compute_all_dimensions(self):
        """Setting analytic_distribution with all four dimensions populates
        every dimension field correctly."""
        distribution = {
            str(self.activity_acc.id): 100,
            str(self.department_acc.id): 100,
            str(self.fund_acc.id): 100,
            str(self.source_acc.id): 100,
        }
        rec = self._create_record(distribution)
        self.assertEqual(rec.activity_analytic_id, self.activity_acc)
        self.assertEqual(rec.department_analytic_id, self.department_acc)
        self.assertEqual(rec.fund_analytic_id, self.fund_acc)
        self.assertEqual(rec.source_analytic_id, self.source_acc)

    def test_compute_empty_distribution(self):
        """Empty or False analytic_distribution leaves dimension fields empty."""
        rec = self._create_record()
        self.assertFalse(rec.activity_analytic_id)
        self.assertFalse(rec.department_analytic_id)
        self.assertFalse(rec.fund_analytic_id)
        self.assertFalse(rec.source_analytic_id)

    # ------------------------------------------------------------------
    # Inverse: dimension field → analytic_distribution
    # ------------------------------------------------------------------

    def test_inverse_single_dimension(self):
        """Writing a single dimension field via inverse updates
        analytic_distribution correctly."""
        rec = self._create_record()
        rec.activity_analytic_id = self.activity_acc
        self.assertEqual(
            rec.analytic_distribution,
            {str(self.activity_acc.id): 100},
        )

    def test_inverse_all_dimensions(self):
        """Writing all four dimension fields produces the correct
        analytic_distribution JSON."""
        rec = self._create_record()
        rec.activity_analytic_id = self.activity_acc
        rec.department_analytic_id = self.department_acc
        rec.fund_analytic_id = self.fund_acc
        rec.source_analytic_id = self.source_acc
        expected = {
            str(self.activity_acc.id): 100,
            str(self.department_acc.id): 100,
            str(self.fund_acc.id): 100,
            str(self.source_acc.id): 100,
        }
        self.assertEqual(rec.analytic_distribution, expected)

    def test_inverse_replace_dimension(self):
        """Changing one dimension replaces only that dimension's entry in
        analytic_distribution while keeping the others intact."""
        activity_acc_2 = self.env["account.analytic.account"].create(
            {
                "name": "Activity 2",
                "code": "TEST_ACT2",
                "plan_id": self.plan_activities.id,
            }
        )
        distribution = {
            str(self.activity_acc.id): 100,
            str(self.department_acc.id): 100,
        }
        rec = self._create_record(distribution)
        # Replace activity while keeping department
        rec.activity_analytic_id = activity_acc_2
        self.assertIn(str(activity_acc_2.id), rec.analytic_distribution)
        self.assertIn(str(self.department_acc.id), rec.analytic_distribution)
        self.assertNotIn(str(self.activity_acc.id), rec.analytic_distribution)

    def test_inverse_clear_dimension(self):
        """Clearing a dimension field removes its entry from
        analytic_distribution."""
        distribution = {
            str(self.activity_acc.id): 100,
            str(self.department_acc.id): 100,
        }
        rec = self._create_record(distribution)
        rec.activity_analytic_id = False
        self.assertNotIn(str(self.activity_acc.id), rec.analytic_distribution or {})
        self.assertIn(str(self.department_acc.id), rec.analytic_distribution or {})

    # ------------------------------------------------------------------
    # Round-trip: dimension field → distribution → dimension field
    # ------------------------------------------------------------------

    def test_roundtrip_set_then_read(self):
        """Setting dimension fields and re-reading them after compute
        returns the same values."""
        rec = self._create_record()
        rec.activity_analytic_id = self.activity_acc
        rec.fund_analytic_id = self.fund_acc
        # Re-trigger compute by invalidating cache
        rec.invalidate_recordset()
        self.assertEqual(rec.activity_analytic_id, self.activity_acc)
        self.assertEqual(rec.fund_analytic_id, self.fund_acc)
        self.assertFalse(rec.department_analytic_id)
        self.assertFalse(rec.source_analytic_id)

    def test_roundtrip_distribution_then_fields(self):
        """Writing analytic_distribution directly and reading dimension fields
        returns correct values after compute."""
        distribution = {
            str(self.department_acc.id): 100,
            str(self.source_acc.id): 100,
        }
        rec = self._create_record()
        rec.analytic_distribution = distribution
        rec.invalidate_recordset()
        self.assertEqual(rec.department_analytic_id, self.department_acc)
        self.assertEqual(rec.source_analytic_id, self.source_acc)
        self.assertFalse(rec.activity_analytic_id)
        self.assertFalse(rec.fund_analytic_id)
