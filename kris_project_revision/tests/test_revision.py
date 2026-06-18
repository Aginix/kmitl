from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKrisProjectRevision(TransactionCase):
    """Revising a project (base_revision) copies the source into a fresh
    draft version, archives the original *and* cancels its state, and
    renumbers KRIS0001 -> KRIS0001-01. Allocations (การจัดสรร), installments
    (งวดงาน) and receipts (บันทึกรายรับ) are all carried across; receipts
    have their installment + allocation cross-links remapped to the new
    revision's records.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env["kris.project"]
        cls.InstallmentAllocation = cls.env["kris.project.installment.allocation"]
        cls.Receipt = cls.env["kris.project.receipt"]

        cls.category = cls.env["kris.project.category"].create(
            {"name": "Revision Test Category"}
        )
        cls.project_type = cls.env["kris.project.type"].create(
            {"name": "Revision Test Type", "category_id": cls.category.id}
        )
        cls.item_a = cls.env["kris.project.allocation.item"].create(
            {"name": "Rev Allocator A", "sequence": 10}
        )
        cls.item_b = cls.env["kris.project.allocation.item"].create(
            {"name": "Rev Allocator B", "sequence": 20}
        )

        # operating_expense = 1,000,000; custom 10% -> base = 100,000
        cls.project = cls.Project.create(
            {
                "project_name": "Revision Source",
                "project_category_id": cls.category.id,
                "project_type_id": cls.project_type.id,
                "project_value": 1_000_000.0,
                "maintenance_deduction_type": "custom",
                "maintenance_deduction_pct": 10.0,
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
                        "sequence": 10,
                    }),
                    (0, 0, {
                        "name": "Installment 2",
                        "amount": 400_000.0,
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
        cls.InstallmentAllocation.create([
            {"installment_id": cls.inst1.id, "allocation_line_id": cls.line_a.id, "amount": 36_000.0},
            {"installment_id": cls.inst1.id, "allocation_line_id": cls.line_b.id, "amount": 24_000.0},
            {"installment_id": cls.inst2.id, "allocation_line_id": cls.line_a.id, "amount": 24_000.0},
            {"installment_id": cls.inst2.id, "allocation_line_id": cls.line_b.id, "amount": 16_000.0},
        ])
        cls.Receipt.create({
            "project_id": cls.project.id,
            "installment_id": cls.inst1.id,
            "name": "RCPT-REV-1",
            "date": "2026-01-01",
            "amount": 100_000.0,
            "allocation_ids": [
                (0, 0, {"allocation_line_id": cls.line_a.id, "amount": 5_000.0}),
                (0, 0, {"allocation_line_id": cls.line_b.id, "amount": 3_000.0}),
            ],
        })

        # A revision is created from a closed (done) project.
        cls.project.write({"state": "done"})
        cls.source_name = cls.project.name

    def _revise(self, project):
        """Run the public create_revision() and return the new draft revision."""
        project.create_revision()
        return project.current_revision_id

    # --- Numbering & identity --------------------------------------------

    def test_revision_numbering_and_identity(self):
        new = self._revise(self.project)
        self.assertEqual(new.name, "%s-01" % self.source_name)
        self.assertEqual(new.revision_number, 1)
        # unrevisioned_name is shared and unchanged across the chain.
        self.assertEqual(new.unrevisioned_name, self.source_name)
        self.assertEqual(self.project.unrevisioned_name, self.source_name)

    def test_revision_keeps_project_name(self):
        # A revision is the same project: no "(copy)" suffix.
        new = self._revise(self.project)
        self.assertEqual(new.project_name, "Revision Source")

    def test_revision_starts_in_draft(self):
        new = self._revise(self.project)
        self.assertEqual(new.state, "draft")
        self.assertTrue(new.active)

    # --- Old revision is archived AND cancelled --------------------------

    def test_old_revision_archived_and_cancelled(self):
        new = self._revise(self.project)
        self.assertFalse(self.project.active)
        # State is forced to cancel via action_cancel() so the workflow agrees
        # with the archive: source is unambiguously inactive.
        self.assertEqual(self.project.state, "cancel")
        self.assertEqual(self.project.current_revision_id, new)
        self.assertIn(self.project, new.old_revision_ids)

    # --- Allocations / installments / receipts copied --------------------

    def test_installments_and_allocations_copied(self):
        new = self._revise(self.project)
        self.assertEqual(len(new.allocation_line_ids), 2)
        self.assertEqual(len(new.installment_ids), 2)
        # Brand-new child records, not shared with the source.
        self.assertFalse(
            set(new.allocation_line_ids.ids) & set(self.project.allocation_line_ids.ids)
        )
        breakdowns = new.installment_ids.mapped("allocation_ids")
        self.assertEqual(len(breakdowns), 4)
        used_line_ids = set(breakdowns.mapped("allocation_line_id").ids)
        self.assertTrue(used_line_ids.issubset(set(new.allocation_line_ids.ids)))
        self.assertFalse(used_line_ids & set(self.project.allocation_line_ids.ids))

    def test_revenue_copied(self):
        new = self._revise(self.project)
        self.assertEqual(len(new.receipt_ids), len(self.project.receipt_ids))
        self.assertEqual(new.total_received_amount, self.project.total_received_amount)
        # Source revenue is untouched.
        self.assertEqual(len(self.project.receipt_ids), 1)

    def test_receipt_installment_remap(self):
        # The seeded receipt is bound to the source's first installment;
        # it must be remapped to the *new* revision's first installment.
        new = self._revise(self.project)
        new_receipt = new.receipt_ids
        self.assertEqual(len(new_receipt), 1)
        new_inst1 = new.installment_ids.filtered(lambda i: i.name == "Installment 1")
        self.assertEqual(new_receipt.installment_id, new_inst1)
        self.assertNotEqual(new_receipt.installment_id, self.inst1)

    def test_receipt_allocation_remap(self):
        # The receipt's allocation breakdown must point at the new revision's
        # allocation lines, not the source's.
        new = self._revise(self.project)
        new_receipt = new.receipt_ids
        new_line_a = new.allocation_line_ids.filtered(
            lambda line: line.item_id == self.item_a
        )
        new_line_b = new.allocation_line_ids.filtered(
            lambda line: line.item_id == self.item_b
        )
        breakdown_lines = new_receipt.allocation_ids.mapped("allocation_line_id")
        self.assertEqual(set(breakdown_lines.ids), {new_line_a.id, new_line_b.id})
        self.assertFalse(breakdown_lines & self.project.allocation_line_ids)

    # --- Revision chain --------------------------------------------------

    def test_second_revision_renumbers_and_relinks_chain(self):
        rev1 = self._revise(self.project)
        rev1.write({"state": "done"})
        rev2 = self._revise(rev1)
        self.assertEqual(rev2.name, "%s-02" % self.source_name)
        self.assertEqual(rev2.revision_number, 2)
        # Both earlier versions now point at the latest revision.
        self.assertEqual(self.project.current_revision_id, rev2)
        self.assertEqual(rev1.current_revision_id, rev2)
        self.assertEqual(set(rev2.old_revision_ids.ids), {self.project.id, rev1.id})

    # --- Action ----------------------------------------------------------

    def test_create_revision_returns_action(self):
        action = self.project.create_revision()
        self.assertEqual(action["res_model"], "kris.project")
        self.assertEqual(action["type"], "ir.actions.act_window")
