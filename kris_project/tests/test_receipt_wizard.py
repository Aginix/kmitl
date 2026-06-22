from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReceiptWizardRemaining(TransactionCase):
    """A single installment (งวดงาน) may be recorded across several receipts.

    The wizard must pre-fill only the amount still outstanding on the
    installment so the 2nd/3rd receipt does not double-count and trip the
    allocation / extra-income guards.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        category = cls.env["kris.project.category"].create({"name": "Cat"})
        project_type = cls.env["kris.project.type"].create(
            {"name": "Type", "category_id": category.id}
        )
        cls.item = cls.env["kris.project.allocation.item"].create({"name": "Dept A"})
        # operating_expense = project_value (no equipment cost); fixed deduction
        # of 200,000 is the allocation pool.
        cls.project = cls.env["kris.project"].create(
            {
                "project_name": "Wizard Project",
                "project_category_id": category.id,
                "project_type_id": project_type.id,
                "project_value": 1_000_000.0,
                "extra_value": 50_000.0,
                "maintenance_deduction_type": "fixed",
                "maintenance_deduction_fixed_amount": 200_000.0,
            }
        )
        cls.alloc_line = cls.env["kris.project.allocation.line"].create(
            {
                "project_id": cls.project.id,
                "item_id": cls.item.id,
                "estimated_amount": 200_000.0,
            }
        )
        cls.installment = cls.env["kris.project.installment"].create(
            {
                "project_id": cls.project.id,
                "name": "งวด 1",
                "amount": 1_000_000.0,
                "extra_income": 50_000.0,
                "allocation_ids": [
                    (0, 0, {"allocation_line_id": cls.alloc_line.id, "amount": 200_000.0})
                ],
            }
        )

    def _open_wizard(self):
        return Form(
            self.env["kris.project.receipt.wizard"].with_context(
                default_project_id=self.project.id
            )
        )

    def _alloc_amount(self, form):
        with form.allocation_ids.edit(0) as line:
            return line.amount

    def test_first_receipt_prefills_full(self):
        f = self._open_wizard()
        f.installment_id = self.installment
        self.assertAlmostEqual(f.amount, 1_000_000.0, places=2)
        self.assertAlmostEqual(f.extra_income, 50_000.0, places=2)
        self.assertAlmostEqual(self._alloc_amount(f), 200_000.0, places=2)

    def test_second_receipt_prefills_remaining_and_saves(self):
        # Receipt #1 records part of the installment.
        receipt1 = self.env["kris.project.receipt"].create(
            {
                "project_id": self.project.id,
                "installment_id": self.installment.id,
                "name": "R1",
                "date": "2026-01-01",
                "amount": 600_000.0,
                "extra_income": 30_000.0,
            }
        )
        self.env["kris.project.receipt.allocation"].create(
            {
                "receipt_id": receipt1.id,
                "allocation_line_id": self.alloc_line.id,
                "amount": 120_000.0,
            }
        )
        self.assertEqual(self.installment.state, "partial")

        # Receipt #2 must pre-fill only what is left, not the full figures.
        f = self._open_wizard()
        f.installment_id = self.installment
        self.assertAlmostEqual(f.amount, 400_000.0, places=2)
        self.assertAlmostEqual(f.extra_income, 20_000.0, places=2)
        self.assertAlmostEqual(self._alloc_amount(f), 80_000.0, places=2)

        # Saving the remaining defaults must not trip the allocation /
        # extra-income guards (this is what the full-figure pre-fill broke).
        f.name = "R2"
        wiz = f.save()
        wiz.action_save()

        self.assertEqual(self.installment.state, "received")
        self.assertAlmostEqual(self.alloc_line.actual_amount, 200_000.0, places=2)

    def test_fully_received_installment_prefills_zero(self):
        # Fully receive the installment in one receipt.
        receipt = self.env["kris.project.receipt"].create(
            {
                "project_id": self.project.id,
                "installment_id": self.installment.id,
                "name": "R1",
                "date": "2026-01-01",
                "amount": 1_000_000.0,
                "extra_income": 50_000.0,
            }
        )
        self.env["kris.project.receipt.allocation"].create(
            {
                "receipt_id": receipt.id,
                "allocation_line_id": self.alloc_line.id,
                "amount": 200_000.0,
            }
        )
        self.assertEqual(self.installment.state, "received")

        # The งวด stays selectable, but defaults to zero so any over-collection
        # is entered deliberately.
        f = self._open_wizard()
        f.installment_id = self.installment
        self.assertAlmostEqual(f.amount, 0.0, places=2)
        self.assertAlmostEqual(f.extra_income, 0.0, places=2)
        self.assertAlmostEqual(self._alloc_amount(f), 0.0, places=2)
