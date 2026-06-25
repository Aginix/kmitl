from datetime import date

from odoo.tests.common import tagged

from .common import KrisProjectCommon


@tagged("post_install", "-at_install")
class TestKrisProjectWizard(KrisProjectCommon):
    """Receipt wizard computations and the save flow."""

    def test_wizard_net_amount(self):
        p = self._make_project()
        wiz = self.Wizard.create(
            {
                "project_id": p.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 100_000.0,
                "deductible_cost_in_installment": 25_000.0,
            }
        )
        self.assertAlmostEqual(wiz.net_amount, 75_000.0, 2)

    def test_wizard_line_remaining_amount(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 100_000.0,
            }
        )
        receipt = self.Receipt.create(
            {
                "project_id": p.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "amount": 50_000.0,
            }
        )
        self.ReceiptAlloc.create(
            {
                "receipt_id": receipt.id,
                "allocation_line_id": line.id,
                "amount": 30_000.0,
            }
        )
        wiz = self.Wizard.create(
            {
                "project_id": p.id,
                "name": "R2",
                "date": date(2025, 1, 1),
                "allocation_ids": [
                    (0, 0, {"allocation_line_id": line.id, "amount": 0.0})
                ],
            }
        )
        wline = wiz.allocation_ids
        self.assertEqual(len(wline), 1)
        # remaining = estimated 100,000 - actual 30,000
        self.assertAlmostEqual(wline.remaining_amount, 70_000.0, 2)

    def test_wizard_onchange_installment_seeds_amounts(self):
        p = self._make_project(
            project_value=1_200_000.0,
            equipment_cost=200_000.0,
            extra_value=5_000.0,
        )
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
                "extra_income": 5_000.0,
            }
        )
        self.InstallmentAlloc.create(
            {
                "installment_id": inst.id,
                "allocation_line_id": line.id,
                "amount": 8_000.0,
            }
        )
        wiz = self.Wizard.create(
            {
                "project_id": p.id,
                "name": "R",
                "date": date(2025, 1, 1),
                "allocation_ids": [
                    (0, 0, {"allocation_line_id": line.id, "amount": 0.0})
                ],
            }
        )
        wiz.installment_id = inst
        wiz._onchange_installment_id()
        # amount and extra_income copied from the installment
        self.assertAlmostEqual(wiz.amount, 100_000.0, 2)
        self.assertAlmostEqual(wiz.extra_income, 5_000.0, 2)
        # the matching installment allocation amount is mapped onto the line
        self.assertAlmostEqual(wiz.allocation_ids.amount, 8_000.0, 2)

    def test_wizard_action_save_creates_receipt_and_allocation(self):
        p = self._make_project(project_value=1_200_000.0, equipment_cost=200_000.0)
        line = self.AllocationLine.create(
            {
                "project_id": p.id,
                "item_id": self.item_a.id,
                "estimated_amount": 100_000.0,
            }
        )
        wiz = self.Wizard.create(
            {
                "project_id": p.id,
                "name": "R-001",
                "date": date(2025, 1, 1),
                "amount": 50_000.0,
                "allocation_ids": [
                    (0, 0, {"allocation_line_id": line.id, "amount": 20_000.0})
                ],
            }
        )
        wiz.action_save()

        receipt = p.receipt_ids
        self.assertEqual(len(receipt), 1)
        self.assertEqual(receipt.name, "R-001")
        self.assertAlmostEqual(receipt.amount, 50_000.0, 2)
        # the saved receipt allocation feeds the allocation line's actual amount
        self.assertAlmostEqual(line.actual_amount, 20_000.0, 2)
