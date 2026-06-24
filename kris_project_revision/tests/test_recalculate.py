from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRecalculateAllocation(TransactionCase):
    """Recalculate re-derives ``estimated_amount`` from the linked template's
    percentages against the current ``maintenance_deduction_amount``, in
    place. Unlike ``action_apply_allocation_template`` it never ``unlink()``s
    rows, so receipts carried from a previous revision keep their
    ``allocation_ids`` linkage and ``actual_amount`` (รับจริง) is preserved.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env["kris.project"]
        cls.Template = cls.env["kris.project.allocation.template"]
        cls.Receipt = cls.env["kris.project.receipt"]
        cls.AllocationLine = cls.env["kris.project.allocation.line"]
        cls.Installment = cls.env["kris.project.installment"]

        cls.category = cls.env["kris.project.category"].create(
            {"name": "Recalc Cat"}
        )
        cls.project_type = cls.env["kris.project.type"].create(
            {"name": "Recalc Type", "category_id": cls.category.id}
        )
        cls.item_a = cls.env["kris.project.allocation.item"].create(
            {"name": "Recalc Allocator A", "sequence": 10}
        )
        cls.item_b = cls.env["kris.project.allocation.item"].create(
            {"name": "Recalc Allocator B", "sequence": 20}
        )
        cls.item_c = cls.env["kris.project.allocation.item"].create(
            {"name": "Recalc Allocator C (manual)", "sequence": 30}
        )

        # Template: 60% / 40% across item_a and item_b.
        cls.template = cls.Template.create(
            {
                "name": "Recalc Template",
                "line_ids": [
                    (0, 0, {
                        "item_id": cls.item_a.id,
                        "sequence": 10,
                        "allocation_pct": 60.0,
                    }),
                    (0, 0, {
                        "item_id": cls.item_b.id,
                        "sequence": 20,
                        "allocation_pct": 40.0,
                    }),
                ],
            }
        )

        # operating_expense = 1,000,000; custom 10% -> base = 100,000.
        # Initial allocation matches the template (60K / 40K).
        cls.project = cls.Project.create(
            {
                "project_name": "Recalc Source",
                "project_category_id": cls.category.id,
                "project_type_id": cls.project_type.id,
                "project_value": 1_000_000.0,
                "maintenance_deduction_type": "custom",
                "maintenance_deduction_pct": 10.0,
                "allocation_template_id": cls.template.id,
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
            }
        )
        cls.line_a = cls.project.allocation_line_ids.filtered(
            lambda line: line.item_id == cls.item_a
        )
        cls.line_b = cls.project.allocation_line_ids.filtered(
            lambda line: line.item_id == cls.item_b
        )

    # --- Happy path -----------------------------------------------------

    def test_recalculate_updates_estimated_from_template(self):
        # Double the project value -> operating_expense=2M, base=200K.
        self.project.project_value = 2_000_000.0
        self.project.action_recalculate_allocation()
        self.assertEqual(self.line_a.estimated_amount, 120_000.0)  # 60% of 200K
        self.assertEqual(self.line_b.estimated_amount, 80_000.0)  # 40% of 200K

    def test_recalculate_preserves_actual_amount(self):
        # Seed an installment + receipt with an allocation breakdown so the
        # allocation lines have a non-zero actual_amount that recalc must
        # leave alone.
        inst = self.Installment.create(
            {
                "project_id": self.project.id,
                "name": "Inst 1",
                "amount": 1_000_000.0,
                "sequence": 10,
            }
        )
        self.Receipt.create(
            {
                "project_id": self.project.id,
                "installment_id": inst.id,
                "name": "RCPT-1",
                "date": "2026-01-01",
                "amount": 100_000.0,
                "allocation_ids": [
                    (0, 0, {
                        "allocation_line_id": self.line_a.id,
                        "amount": 5_000.0,
                    }),
                    (0, 0, {
                        "allocation_line_id": self.line_b.id,
                        "amount": 3_000.0,
                    }),
                ],
            }
        )
        self.assertEqual(self.line_a.actual_amount, 5_000.0)
        self.assertEqual(self.line_b.actual_amount, 3_000.0)

        self.project.project_value = 2_000_000.0
        self.project.action_recalculate_allocation()

        # estimated_amount updated...
        self.assertEqual(self.line_a.estimated_amount, 120_000.0)
        self.assertEqual(self.line_b.estimated_amount, 80_000.0)
        # ...but actual_amount (รับจริง) is untouched: the receipt allocation
        # rows still exist and still point at the same lines.
        self.assertEqual(self.line_a.actual_amount, 5_000.0)
        self.assertEqual(self.line_b.actual_amount, 3_000.0)

    # --- Edge cases -----------------------------------------------------

    def test_recalculate_skips_locked_lines(self):
        self.line_a.is_locked = True
        self.project.project_value = 2_000_000.0
        self.project.action_recalculate_allocation()
        self.assertEqual(self.line_a.estimated_amount, 60_000.0)
        self.assertEqual(self.line_b.estimated_amount, 80_000.0)

    def test_recalculate_no_template_raises(self):
        self.project.allocation_template_id = False
        with self.assertRaises(UserError):
            self.project.action_recalculate_allocation()

    def test_recalculate_leaves_extra_line_alone(self):
        # Manually added line whose item_id is not in the template.
        extra = self.AllocationLine.create(
            {
                "project_id": self.project.id,
                "item_id": self.item_c.id,
                "estimated_amount": 5_000.0,
                "sequence": 30,
            }
        )
        self.project.project_value = 2_000_000.0
        self.project.action_recalculate_allocation()
        self.assertEqual(self.line_a.estimated_amount, 120_000.0)
        self.assertEqual(self.line_b.estimated_amount, 80_000.0)
        self.assertEqual(extra.estimated_amount, 5_000.0)
