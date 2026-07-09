from datetime import date

from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResearchInCashInKind(TransactionCase):
    """The research category splits project_value into in_cash + in_kind.

    All cash-flow computations (operating expense, maintenance deduction,
    revenue remaining, installment total-mismatch warning) must anchor on
    in_cash and never on the derived project_value — in-kind money never
    reaches KRIS.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env["kris.project"]
        cls.Installment = cls.env["kris.project.installment"]
        cls.Receipt = cls.env["kris.project.receipt"]

        # Research category / type from the seed data — the compute gates on
        # this exact xmlid.
        cls.research_category = cls.env.ref(
            "kris_project.project_category_research"
        )
        cls.research_type = cls.env.ref(
            "kris_project.project_type_external_research"
        )

        # A fresh non-research category to prove nothing changes on the
        # non-research branch.
        cls.other_category = cls.env["kris.project.category"].create(
            {"name": "Non-Research Category"}
        )
        cls.other_type = cls.env["kris.project.type"].create(
            {"name": "Non-Research Type", "category_id": cls.other_category.id}
        )

    def _make_research_project(self, **vals):
        base = {
            "project_name": "Research Test",
            "project_category_id": self.research_category.id,
            "project_type_id": self.research_type.id,
        }
        base.update(vals)
        return self.Project.create(base)

    # -- Field derivation -------------------------------------------------

    def test_project_value_is_derived_from_in_cash_plus_in_kind(self):
        project = self._make_research_project(in_cash=800_000.0, in_kind=200_000.0)
        self.assertEqual(project.project_value, 1_000_000.0)
        self.assertTrue(project.is_research_category)

    def test_project_value_recomputes_when_in_cash_changes(self):
        project = self._make_research_project(in_cash=500_000.0, in_kind=100_000.0)
        project.in_cash = 900_000.0
        self.assertEqual(project.project_value, 1_000_000.0)

    def test_cash_target_is_in_cash_for_research(self):
        project = self._make_research_project(in_cash=800_000.0, in_kind=200_000.0)
        self.assertEqual(project.cash_target, 800_000.0)

    # -- Downstream cash-flow anchors on in_cash -------------------------

    def test_operating_expense_excludes_in_kind(self):
        # cash_target = in_cash (800k); operating_expense = 800k - 0 = 800k,
        # NOT 1M - 0.
        project = self._make_research_project(in_cash=800_000.0, in_kind=200_000.0)
        self.assertEqual(project.operating_expense, 800_000.0)

    def test_operating_expense_deducts_equipment_from_in_cash(self):
        project = self._make_research_project(
            in_cash=1_000_000.0, in_kind=500_000.0, equipment_cost=200_000.0
        )
        self.assertEqual(project.operating_expense, 800_000.0)

    def test_maintenance_deduction_ignores_in_kind(self):
        # Tiered: 800k operating -> 800k * 10% = 80,000 (all in the first
        # bracket). If in_kind leaked in the maintenance base would be 1M
        # and the answer would be 100,000.
        project = self._make_research_project(
            in_cash=800_000.0,
            in_kind=200_000.0,
            maintenance_deduction_type="tiered",
        )
        self.assertAlmostEqual(
            project.maintenance_deduction_amount, 80_000.0, places=2
        )

    def test_revenue_remaining_anchors_on_in_cash(self):
        # Receipts total the full in_cash target -> revenue_remaining = 0
        # even though project_value (in_cash + in_kind) is larger.
        project = self._make_research_project(in_cash=500_000.0, in_kind=200_000.0)
        self.Receipt.create(
            {
                "project_id": project.id,
                "name": "R1",
                "date": date(2025, 1, 1),
                "amount": 500_000.0,
            }
        )
        self.assertEqual(project.revenue_remaining, 0.0)
        self.assertEqual(project.over_revenue, 0.0)

    def test_warn_installment_total_mismatch_anchors_on_in_cash(self):
        # Installments summing to in_cash must NOT trip the warning even
        # though total_installment_amount < project_value (which includes
        # in_kind).
        project = self._make_research_project(in_cash=600_000.0, in_kind=400_000.0)
        self.Installment.create(
            {
                "project_id": project.id,
                "name": "งวด 1",
                "amount": 600_000.0,
            }
        )
        self.assertFalse(project.warn_installment_total_mismatch)

    # -- Onchange backfill -----------------------------------------------

    def test_switching_into_research_backfills_in_cash(self):
        # A draft non-research project with project_value=1M is switched to
        # research; the onchange seeds in_cash from the existing project_value
        # so the derivation does not wipe the amount.
        form = Form(self.Project)
        form.project_name = "Switching In"
        form.project_category_id = self.other_category
        form.project_type_id = self.other_type
        form.project_value = 1_000_000.0

        form.project_category_id = self.research_category
        form.project_type_id = self.research_type

        self.assertEqual(form.in_cash, 1_000_000.0)
        self.assertEqual(form.in_kind, 0.0)
        self.assertEqual(form.project_value, 1_000_000.0)

    def test_switching_into_research_does_not_overwrite_existing_in_cash(self):
        # If in_cash/in_kind are already set, switching category must not
        # overwrite them from project_value.
        form = Form(self.Project)
        form.project_name = "Preserve Existing"
        form.project_category_id = self.research_category
        form.project_type_id = self.research_type
        form.in_cash = 700_000.0
        form.in_kind = 300_000.0

        form.project_category_id = self.other_category
        form.project_type_id = self.other_type
        form.project_category_id = self.research_category
        form.project_type_id = self.research_type

        self.assertEqual(form.in_cash, 700_000.0)
        self.assertEqual(form.in_kind, 300_000.0)

    # -- Non-research is untouched ---------------------------------------

    def test_non_research_project_value_is_user_input(self):
        project = self.Project.create(
            {
                "project_name": "Non-Research",
                "project_category_id": self.other_category.id,
                "project_type_id": self.other_type.id,
                "project_value": 1_500_000.0,
            }
        )
        self.assertFalse(project.is_research_category)
        self.assertEqual(project.project_value, 1_500_000.0)
        self.assertEqual(project.cash_target, 1_500_000.0)
        self.assertEqual(project.operating_expense, 1_500_000.0)
