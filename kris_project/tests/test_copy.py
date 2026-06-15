from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKrisProjectCopy(TransactionCase):
    """Duplicating a project keeps the allocation (การจัดสรร) and installments
    (งวดงาน) but never the revenue (รายรับ), and renames clashes with "(copy)".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env["kris.project"]
        cls.InstallmentAllocation = cls.env["kris.project.installment.allocation"]
        cls.Receipt = cls.env["kris.project.receipt"]

        cls.category = cls.env["kris.project.category"].create(
            {"name": "Copy Test Category"}
        )
        cls.project_type = cls.env["kris.project.type"].create(
            {"name": "Copy Test Type", "category_id": cls.category.id}
        )
        cls.item_a = cls.env["kris.project.allocation.item"].create(
            {"name": "Allocator A", "sequence": 10}
        )
        cls.item_b = cls.env["kris.project.allocation.item"].create(
            {"name": "Allocator B", "sequence": 20}
        )

        # operating_expense = 1,000,000; custom 10% -> base = 100,000
        cls.project = cls.Project.create(
            {
                "project_name": "Copy Source",
                "project_category_id": cls.category.id,
                "project_type_id": cls.project_type.id,
                "project_value": 1_000_000.0,
                "maintenance_deduction_type": "custom",
                "maintenance_deduction_pct": 10.0,
                "extra_value": 50_000.0,
                "allocation_line_ids": [
                    (0, 0, {
                        "item_id": cls.item_a.id,
                        "estimated_amount": 60_000.0,
                        "sequence": 10,
                    }),
                    (0, 0, {
                        "item_id": cls.item_b.id,
                        "estimated_amount": 40_000.0,
                        "sequence": 20,
                    }),
                ],
                "installment_ids": [
                    (0, 0, {
                        "name": "Installment 1",
                        "amount": 600_000.0,
                        "extra_income": 30_000.0,
                        "sequence": 10,
                    }),
                    (0, 0, {
                        "name": "Installment 2",
                        "amount": 400_000.0,
                        "extra_income": 20_000.0,
                        "sequence": 20,
                    }),
                ],
            }
        )
        cls.line_a = cls.project.allocation_line_ids.filtered(
            lambda line: line.item_id == cls.item_a
        )
        cls.line_b = cls.project.allocation_line_ids.filtered(
            lambda line: line.item_id == cls.item_b
        )
        cls.inst1 = cls.project.installment_ids.filtered(
            lambda inst: inst.name == "Installment 1"
        )
        cls.inst2 = cls.project.installment_ids.filtered(
            lambda inst: inst.name == "Installment 2"
        )

        # Per-installment maintenance breakdown: the model that cross-references
        # both the installment AND the allocation line (the tricky part to copy).
        cls.InstallmentAllocation.create([
            {"installment_id": cls.inst1.id, "allocation_line_id": cls.line_a.id, "amount": 36_000.0},
            {"installment_id": cls.inst1.id, "allocation_line_id": cls.line_b.id, "amount": 24_000.0},
            {"installment_id": cls.inst2.id, "allocation_line_id": cls.line_a.id, "amount": 24_000.0},
            {"installment_id": cls.inst2.id, "allocation_line_id": cls.line_b.id, "amount": 16_000.0},
        ])

        # Revenue (รายรับ) with its own allocation breakdown: must NOT be copied.
        cls.Receipt.create({
            "project_id": cls.project.id,
            "installment_id": cls.inst1.id,
            "name": "RCPT-1",
            "date": "2026-01-01",
            "amount": 100_000.0,
            "extra_income": 10_000.0,
            "allocation_ids": [
                (0, 0, {"allocation_line_id": cls.line_a.id, "amount": 5_000.0}),
                (0, 0, {"allocation_line_id": cls.line_b.id, "amount": 3_000.0}),
            ],
        })

    # --- Project number / name -------------------------------------------

    def test_project_number_is_regenerated(self):
        # name has copy=False, so the duplicate draws a fresh sequence number.
        copy = self.project.copy()
        self.assertTrue(self.project.name and self.project.name != "New")
        self.assertNotEqual(copy.name, self.project.name)
        self.assertNotIn("New", copy.name)

    def test_name_gets_copy_suffix_on_clash(self):
        # A duplicate always clashes with its source, so the suffix is added.
        copy = self.project.copy()
        self.assertEqual(copy.project_name, "Copy Source (copy)")

    def test_explicit_name_in_default_skips_suffix(self):
        # An explicit name passed by the caller is respected verbatim.
        copy = self.project.copy({"project_name": "A Totally Different Name"})
        self.assertEqual(copy.project_name, "A Totally Different Name")

    def test_repeated_copy_stacks_suffix(self):
        first = self.project.copy()
        second = first.copy()
        self.assertEqual(first.project_name, "Copy Source (copy)")
        self.assertEqual(second.project_name, "Copy Source (copy) (copy)")

    # --- Allocation (การจัดสรร) ------------------------------------------

    def test_allocation_lines_are_copied(self):
        copy = self.project.copy()
        self.assertEqual(len(copy.allocation_line_ids), 2)
        # Brand-new records, not the source ones.
        self.assertFalse(
            set(copy.allocation_line_ids.ids) & set(self.project.allocation_line_ids.ids)
        )
        self.assertEqual(
            sorted(copy.allocation_line_ids.mapped("estimated_amount")),
            [40_000.0, 60_000.0],
        )
        self.assertEqual(
            copy.allocation_line_ids.mapped("item_id"),
            self.item_a + self.item_b,
        )

    # --- Installments (งวดงาน) -------------------------------------------

    def test_installments_are_copied_with_maintenance_fee(self):
        copy = self.project.copy()
        self.assertEqual(len(copy.installment_ids), 2)
        self.assertFalse(
            set(copy.installment_ids.ids) & set(self.project.installment_ids.ids)
        )
        by_name = {inst.name: inst for inst in copy.installment_ids}
        self.assertAlmostEqual(by_name["Installment 1"].amount, 600_000.0, places=2)
        self.assertAlmostEqual(by_name["Installment 2"].amount, 400_000.0, places=2)
        # maintenance_fee is derived from the rebuilt breakdown.
        self.assertAlmostEqual(by_name["Installment 1"].maintenance_fee, 60_000.0, places=2)
        self.assertAlmostEqual(by_name["Installment 2"].maintenance_fee, 40_000.0, places=2)

    def test_installment_allocation_breakdown_is_remapped(self):
        # The breakdown must point at the COPY's allocation lines, never the
        # source's, otherwise the two projects would share allocation rows.
        copy = self.project.copy()
        breakdowns = copy.installment_ids.mapped("allocation_ids")
        self.assertEqual(len(breakdowns), 4)
        used_line_ids = set(breakdowns.mapped("allocation_line_id").ids)
        self.assertTrue(used_line_ids.issubset(set(copy.allocation_line_ids.ids)))
        self.assertFalse(used_line_ids & set(self.project.allocation_line_ids.ids))
        self.assertAlmostEqual(sum(breakdowns.mapped("amount")), 100_000.0, places=2)

    def test_breakdown_amounts_match_per_installment(self):
        copy = self.project.copy()
        by_name = {inst.name: inst for inst in copy.installment_ids}
        self.assertEqual(
            sorted(by_name["Installment 1"].allocation_ids.mapped("amount")),
            [24_000.0, 36_000.0],
        )
        self.assertEqual(
            sorted(by_name["Installment 2"].allocation_ids.mapped("amount")),
            [16_000.0, 24_000.0],
        )

    # --- Revenue (รายรับ) must not be copied -----------------------------

    def test_revenue_is_not_copied(self):
        copy = self.project.copy()
        self.assertFalse(copy.receipt_ids)
        self.assertAlmostEqual(copy.total_received_amount, 0.0, places=2)
        # Revenue-derived allocation actuals start clean on the copy.
        self.assertFalse(copy.allocation_line_ids.mapped("receipt_allocation_ids"))
        self.assertEqual(set(copy.allocation_line_ids.mapped("actual_amount")), {0.0})
        # The source keeps its revenue untouched.
        self.assertEqual(len(self.project.receipt_ids), 1)
