from datetime import date

from odoo.tests.common import tagged

from odoo.addons.kris_project.models.kris_project import _compute_tiered_deduction

from .common import KrisProjectCommon


@tagged("post_install", "-at_install")
class TestKrisProjectCompute(KrisProjectCommon):
    """Project-level financial computations on ``kris.project``."""

    # ------------------------------------------------------------------
    # Progressive tiered deduction helper
    #   0 – 1,000,000        → 10 %
    #   1,000,001 – 5,000,000  → 9 %
    #   5,000,001 – 10,000,000 → 8 %
    #   > 10,000,000           → 7 %
    # ------------------------------------------------------------------
    def test_tiered_zero(self):
        self.assertAlmostEqual(_compute_tiered_deduction(0.0), 0.0, 2)

    def test_tiered_within_first_bracket(self):
        # 500,000 * 10%
        self.assertAlmostEqual(_compute_tiered_deduction(500_000.0), 50_000.0, 2)

    def test_tiered_first_bracket_cap(self):
        # 1,000,000 * 10%
        self.assertAlmostEqual(_compute_tiered_deduction(1_000_000.0), 100_000.0, 2)

    def test_tiered_second_bracket(self):
        # 100,000 + (3,000,000 - 1,000,000) * 9% = 100,000 + 180,000
        self.assertAlmostEqual(_compute_tiered_deduction(3_000_000.0), 280_000.0, 2)

    def test_tiered_second_bracket_cap(self):
        # 100,000 + (5,000,000 - 1,000,000) * 9% = 100,000 + 360,000
        self.assertAlmostEqual(_compute_tiered_deduction(5_000_000.0), 460_000.0, 2)

    def test_tiered_third_bracket_cap(self):
        # 460,000 + (10,000,000 - 5,000,000) * 8% = 460,000 + 400,000
        self.assertAlmostEqual(_compute_tiered_deduction(10_000_000.0), 860_000.0, 2)

    def test_tiered_top_bracket(self):
        # 860,000 + (12,000,000 - 10,000,000) * 7% = 860,000 + 140,000
        self.assertAlmostEqual(_compute_tiered_deduction(12_000_000.0), 1_000_000.0, 2)

    # ------------------------------------------------------------------
    # operating_expense / allocatable_value
    # ------------------------------------------------------------------
    def test_operating_expense(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        self.assertAlmostEqual(p.operating_expense, 1_000_000.0, 2)

    def test_allocatable_value_equals_operating_expense(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        self.assertAlmostEqual(p.allocatable_value, 1_000_000.0, 2)

    # ------------------------------------------------------------------
    # maintenance_deduction_amount: tiered vs custom (on operating_expense)
    # ------------------------------------------------------------------
    def test_maintenance_deduction_tiered(self):
        # operating_expense = 1,000,000 → tiered 100,000
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        self.assertAlmostEqual(p.maintenance_deduction_amount, 100_000.0, 2)

    def test_maintenance_deduction_custom(self):
        # operating_expense = 1,000,000 * 15% = 150,000
        p = self._make_project(
            project_value=1_200_000.0,
            equipment_cost=200_000.0,
            maintenance_deduction_type="custom",
            maintenance_deduction_pct=15.0,
        )
        self.assertAlmostEqual(p.maintenance_deduction_amount, 150_000.0, 2)

    # ------------------------------------------------------------------
    # project_duration (inclusive day count)
    # ------------------------------------------------------------------
    def test_project_duration_inclusive(self):
        p = self._make_project(
            date_contract_start=date(2025, 1, 1),
            date_contract_end=date(2025, 1, 10),
        )
        self.assertEqual(p.project_duration, 10)

    def test_project_duration_no_dates(self):
        p = self._make_project()
        self.assertEqual(p.project_duration, 0)

    # ------------------------------------------------------------------
    # can_edit
    # ------------------------------------------------------------------
    def test_can_edit_is_true_in_draft(self):
        p = self._make_project()
        self.assertTrue(p.can_edit)

    # ------------------------------------------------------------------
    # totals: installment / received / net / extra / remaining / over
    # ------------------------------------------------------------------
    def test_totals_basic(self):
        p = self._make_project(project_value=1_000_000.0)
        self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 400_000.0}
        )
        self.Installment.create(
            {"project_id": p.id, "name": "งวด 2", "amount": 600_000.0}
        )
        self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R1",
                "date": date(2025, 1, 1),
                "amount": 300_000.0,
                "equipment_cost_in_installment": 50_000.0,
            }
        )
        self.assertAlmostEqual(p.total_installment_amount, 1_000_000.0, 2)
        self.assertAlmostEqual(p.total_received_amount, 300_000.0, 2)
        # net = amount - equipment_cost_in_installment = 300,000 - 50,000
        self.assertAlmostEqual(p.total_net_received, 250_000.0, 2)
        self.assertAlmostEqual(p.revenue_remaining, 700_000.0, 2)
        self.assertAlmostEqual(p.over_revenue, 0.0, 2)

    def test_totals_over_revenue(self):
        p = self._make_project(project_value=1_000_000.0)
        self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R1",
                "date": date(2025, 1, 1),
                "amount": 1_200_000.0,
            }
        )
        self.assertAlmostEqual(p.revenue_remaining, 0.0, 2)
        self.assertAlmostEqual(p.over_revenue, 200_000.0, 2)

    def test_totals_extra_received(self):
        p = self._make_project(project_value=1_000_000.0, extra_value=100_000.0)
        self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R1",
                "date": date(2025, 1, 1),
                "amount": 100_000.0,
                "extra_income": 30_000.0,
            }
        )
        self.assertAlmostEqual(p.total_extra_received, 30_000.0, 2)

    # ------------------------------------------------------------------
    # warning flags
    # ------------------------------------------------------------------
    def test_warn_allocation_mismatch(self):
        # maintenance_deduction_amount = 100,000; allocation total 40,000 ≠ 100,000
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 40_000.0,
            }
        )
        self.assertTrue(p.warn_allocation_mismatch)

    def test_no_warn_allocation_when_matched(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 100_000.0,
            }
        )
        self.assertFalse(p.warn_allocation_mismatch)

    def test_warn_installment_total_mismatch(self):
        # total installment 400,000 ≠ project_value 1,000,000
        p = self._make_project(project_value=1_000_000.0)
        self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 400_000.0}
        )
        self.assertTrue(p.warn_installment_total_mismatch)

    def test_warn_installment_maintenance_mismatch(self):
        # installment exists, no allocation breakdown → maintenance_fee total 0
        # ≠ maintenance_deduction_amount 100,000
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 1_200_000.0}
        )
        self.assertTrue(p.warn_installment_maintenance_mismatch)
        # installment total 1,200,000 == project_value → no total mismatch
        self.assertFalse(p.warn_installment_total_mismatch)

    def test_warn_extra_overshoot(self):
        p = self._make_project(project_value=1_000_000.0, extra_value=50_000.0)
        self.Installment.create(
            {
                "project_id": p.id,
                "name": "งวด 1",
                "amount": 100_000.0,
                "extra_income": 50_000.0,
            }
        )
        # equal to extra_value → not an overshoot
        self.assertFalse(p.warn_extra_overshoot)
        # lower the project extra ceiling below the booked installment extra
        p.extra_value = 40_000.0
        self.assertTrue(p.warn_extra_overshoot)

    # ------------------------------------------------------------------
    # action_apply_allocation_template
    # ------------------------------------------------------------------
    def test_apply_allocation_template(self):
        # maintenance_deduction_amount = 100,000
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        template = self.Template.create({"name": "T"})
        self.TemplateLine.create(
            {
                "template_id": template.id,
                "item_id": self.item_a.id,
                "sequence": 10,
                "allocation_pct": 70.0,
            }
        )
        self.TemplateLine.create(
            {
                "template_id": template.id,
                "item_id": self.item_b.id,
                "sequence": 20,
                "allocation_pct": 30.0,
            }
        )
        p.allocation_template_id = template
        p.action_apply_allocation_template()

        lines = p.allocation_line_ids.sorted("sequence")
        self.assertEqual(len(lines), 2)
        # estimated = base * pct / 100
        self.assertAlmostEqual(lines[0].estimated_amount, 70_000.0, 2)
        self.assertAlmostEqual(lines[1].estimated_amount, 30_000.0, 2)
        self.assertAlmostEqual(sum(lines.mapped("estimated_amount")), 100_000.0, 2)
        # allocation_pct recomputed from estimated / base
        self.assertAlmostEqual(lines[0].allocation_pct, 70.0, 2)
        self.assertFalse(p.warn_allocation_mismatch)
