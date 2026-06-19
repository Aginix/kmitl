from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import KrisProjectCommon


@tagged("post_install", "-at_install")
class TestKrisProjectLines(KrisProjectCommon):
    """Computations and guard constraints on installment / receipt /
    allocation lines."""

    # ------------------------------------------------------------------
    # Installment computations
    # ------------------------------------------------------------------
    def test_installment_received_from_employer(self):
        p = self._make_project()
        inst = self.Installment.create(
            {
                "project_id": p.id,
                "name": "งวด 1",
                "amount": 100_000.0,
                "deduction_guarantee": 5_000.0,
                "deduction_advance": 3_000.0,
            }
        )
        # 100,000 - 5,000 - 3,000
        self.assertAlmostEqual(inst.received_from_employer, 92_000.0, 2)

    def test_installment_maintenance_fee_and_net(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 100_000.0,
            }
        )
        inst = self.Installment.create(
            {
                "project_id": p.id,
                "name": "งวด 1",
                "amount": 100_000.0,
                "deduction_guarantee": 10_000.0,
                "extra_deduction": 2_000.0,
            }
        )
        self.InstallmentAlloc.create(
            {
                "installment_id": inst.id,
                "allocation_line_id": line.id,
                "amount": 8_000.0,
            }
        )
        # maintenance_fee = sum(allocation_ids.amount)
        self.assertAlmostEqual(inst.maintenance_fee, 8_000.0, 2)
        # received_from_employer = 100,000 - 10,000 = 90,000
        # amount_net = 90,000 - 8,000 - 2,000 - 0 = 80,000
        self.assertAlmostEqual(inst.amount_net, 80_000.0, 2)

    def test_installment_state_pending(self):
        p = self._make_project()
        inst = self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 100_000.0}
        )
        self.assertEqual(inst.state, "pending")
        self.assertAlmostEqual(inst.received_total, 0.0, 2)

    def test_installment_state_partial(self):
        p = self._make_project()
        inst = self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 100_000.0}
        )
        self.Receipt.create(
            {
                "project_id": p.id,
                "installment_id": inst.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 40_000.0,
            }
        )
        self.assertEqual(inst.state, "partial")
        self.assertAlmostEqual(inst.received_total, 40_000.0, 2)

    def test_installment_state_received(self):
        p = self._make_project()
        inst = self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 100_000.0}
        )
        self.Receipt.create(
            {
                "project_id": p.id,
                "installment_id": inst.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 100_000.0,
            }
        )
        self.assertEqual(inst.state, "received")

    # ------------------------------------------------------------------
    # Receipt computations
    # ------------------------------------------------------------------
    def test_receipt_net_amount(self):
        p = self._make_project()
        receipt = self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 100_000.0,
                "equipment_cost_in_installment": 20_000.0,
            }
        )
        self.assertAlmostEqual(receipt.net_amount, 80_000.0, 2)

    # ------------------------------------------------------------------
    # Allocation line computations
    # ------------------------------------------------------------------
    def test_allocation_pct(self):
        # base (maintenance_deduction_amount) = 100,000; 35,000 / 100,000 * 100
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 35_000.0,
            }
        )
        self.assertAlmostEqual(line.allocation_pct, 35.0, 2)

    def test_allocation_pct_zero_base(self):
        # no project value → maintenance base 0 → pct guarded to 0
        p = self._make_project()
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 0.0,
            }
        )
        self.assertAlmostEqual(line.allocation_pct, 0.0, 2)

    def test_allocation_actual_amount(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 50_000.0,
            }
        )
        receipt = self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 100_000.0,
            }
        )
        self.ReceiptAlloc.create(
            {
                "receipt_id": receipt.id,
                "allocation_line_id": line.id,
                "amount": 30_000.0,
            }
        )
        self.assertAlmostEqual(line.actual_amount, 30_000.0, 2)

    # ------------------------------------------------------------------
    # Installment allocation breakdown: allocated/remaining across
    # OTHER installments of the same allocation line
    # ------------------------------------------------------------------
    def test_installment_allocation_remaining(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 100_000.0,
            }
        )
        inst1 = self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 100_000.0}
        )
        inst2 = self.Installment.create(
            {"project_id": p.id, "name": "งวด 2", "amount": 100_000.0}
        )
        self.InstallmentAlloc.create(
            {
                "installment_id": inst1.id,
                "allocation_line_id": line.id,
                "amount": 30_000.0,
            }
        )
        ia2 = self.InstallmentAlloc.create(
            {
                "installment_id": inst2.id,
                "allocation_line_id": line.id,
                "amount": 0.0,
            }
        )
        # Read on an isolated single-record recordset so the compute excludes
        # only inst2 and counts inst1's 30,000.
        self.env.invalidate_all()
        ia2 = self.InstallmentAlloc.browse(ia2.id)
        self.assertAlmostEqual(ia2.allocated_amount, 30_000.0, 2)
        self.assertAlmostEqual(ia2.remaining_amount, 70_000.0, 2)

    def test_installment_allocation_no_siblings(self):
        # The record's OWN installment is excluded; with no other installment
        # allocating to the line, allocated stays 0 and remaining == estimated.
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 100_000.0,
            }
        )
        inst = self.Installment.create(
            {"project_id": p.id, "name": "งวด 1", "amount": 100_000.0}
        )
        ia = self.InstallmentAlloc.create(
            {
                "installment_id": inst.id,
                "allocation_line_id": line.id,
                "amount": 25_000.0,
            }
        )
        self.env.invalidate_all()
        ia = self.InstallmentAlloc.browse(ia.id)
        self.assertAlmostEqual(ia.allocated_amount, 0.0, 2)
        self.assertAlmostEqual(ia.remaining_amount, 100_000.0, 2)

    # ------------------------------------------------------------------
    # Guard constraints (calculation integrity)
    # ------------------------------------------------------------------
    def test_constraint_estimated_sum_exceeds_base(self):
        # base = 100,000; single line of 150,000 exceeds it
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        with self.assertRaises(ValidationError):
            self.AllocationLine.create(
                {
                    "project_id": p.id,
                    "item_id": self.item_a.id,
                    "estimated_amount": 150_000.0,
                }
            )

    def test_constraint_receipt_alloc_exceeds_estimated(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 50_000.0,
            }
        )
        receipt = self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 100_000.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.ReceiptAlloc.create(
                {
                    "receipt_id": receipt.id,
                    "allocation_line_id": line.id,
                    "amount": 60_000.0,
                }
            )

    def test_constraint_alloc_line_actual_exceeds_estimated(self):
        # The line-level guard (distinct from the receipt.allocation one):
        # lowering estimated below an already-booked actual must raise.
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 50_000.0,
            }
        )
        receipt = self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 100_000.0,
            }
        )
        self.ReceiptAlloc.create(
            {
                "receipt_id": receipt.id,
                "allocation_line_id": line.id,
                "amount": 40_000.0,
            }
        )
        self.assertAlmostEqual(line.actual_amount, 40_000.0, 2)
        with self.assertRaises(ValidationError):
            line.estimated_amount = 30_000.0

    def test_constraint_installment_extra_exceeds_project(self):
        p = self._make_project(project_value=1_000_000.0, extra_value=10_000.0)
        with self.assertRaises(ValidationError):
            self.Installment.create(
                {
                    "project_id": p.id,
                    "name": "งวด 1",
                    "amount": 100_000.0,
                    "extra_income": 20_000.0,
                }
            )

    def test_constraint_receipt_extra_exceeds_project(self):
        p = self._make_project(project_value=1_000_000.0, extra_value=10_000.0)
        with self.assertRaises(ValidationError):
            self.Receipt.create(
                {
                    "project_id": p.id,
                    "name": "R",
                    "date": date(2025, 1, 1),
                    "amount": 100_000.0,
                    "extra_income": 20_000.0,
                }
            )
