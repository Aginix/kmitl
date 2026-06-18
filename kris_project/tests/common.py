from odoo.tests.common import TransactionCase


class KrisProjectCommon(TransactionCase):
    """Shared setup for KRIS Project calculation tests.

    Builds the minimal master data (category, type, allocation items) so each
    test can spin up a project with ``_make_project`` and exercise the
    computed/financial fields in isolation.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env["kris.project"]
        cls.Installment = cls.env["kris.project.installment"]
        cls.Receipt = cls.env["kris.project.receipt"]
        cls.AllocationLine = cls.env["kris.project.allocation.line"]
        cls.AllocationItem = cls.env["kris.project.allocation.item"]
        cls.Template = cls.env["kris.project.allocation.template"]
        cls.TemplateLine = cls.env["kris.project.allocation.template.line"]
        cls.ReceiptAlloc = cls.env["kris.project.receipt.allocation"]
        cls.InstallmentAlloc = cls.env["kris.project.installment.allocation"]
        cls.Wizard = cls.env["kris.project.receipt.wizard"]

        cls.category = cls.env["kris.project.category"].create(
            {"name": "Test Category"}
        )
        cls.ptype = cls.env["kris.project.type"].create(
            {"name": "Test Type", "category_id": cls.category.id}
        )

        # Generic allocation items (names irrelevant to the math).
        cls.item_a = cls.AllocationItem.create({"name": "Alloc A", "sequence": 10})
        cls.item_b = cls.AllocationItem.create({"name": "Alloc B", "sequence": 20})

    def _make_project(self, **vals):
        """Create a draft project with the required fields prefilled."""
        base = {
            "project_name": "Test Project",
            "project_category_id": self.category.id,
            "project_type_id": self.ptype.id,
        }
        base.update(vals)
        return self.Project.create(base)
