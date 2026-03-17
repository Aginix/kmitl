# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseOrderProcurementCommittee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.committee_model = cls.env["procurement.committee"]
        cls.wiz = cls.env["purchase.request.line.make.purchase.order"]
        cls.department = cls.env["hr.department"].create(
            {"name": "Test Department", "short_name": "TEST"}
        )
        cls.employee1 = cls.env["hr.employee"].create(
            {"name": "Test Employee 1", "department_id": cls.department.id}
        )
        cls.employee2 = cls.env["hr.employee"].create(
            {"name": "Test Employee 2", "department_id": cls.department.id}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Vendor"})
        cls.product1 = cls.env["product.product"].create({"name": "Test Product"})
        cls.picking_type = cls.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )

    def _create_approved_pr(self, with_work_supervisor=True):
        """Create a PR with required committees and advance to approved state."""
        pr = self.env["purchase.request"].create(
            {
                "picking_type_id": self.picking_type.id,
                "requested_by": SUPERUSER_ID,
                "department_id": self.department.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product1.id,
                            "product_uom_id": self.env.ref(
                                "uom.product_uom_unit"
                            ).id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                            "estimated_cost": 100.0,
                        },
                    )
                ],
            }
        )
        self.committee_model.create(
            {
                "name": self.employee1.display_name,
                "employee_id": self.employee1.id,
                "approve_role": "chairman",
                "committee_type": "work_acceptance",
                "request_id": pr.id,
            }
        )
        if with_work_supervisor:
            self.committee_model.create(
                {
                    "name": self.employee2.display_name,
                    "employee_id": self.employee2.id,
                    "approve_role": "committee",
                    "committee_type": "work_supervisor",
                    "request_id": pr.id,
                }
            )
        pr.button_to_approve()
        pr.button_approved()
        return pr

    def _make_purchase_order(self, pr):
        """Run the wizard and return the created PO."""
        wiz = self.wiz.with_context(
            active_model="purchase.request",
            active_ids=[pr.id],
            active_id=pr.id,
        ).create({"supplier_id": self.partner.id})
        wiz.make_purchase_order()
        return pr.line_ids.purchase_lines.order_id

    def test_01_committee_propagation_to_purchase_order(self):
        """Committees from PR are copied to the PO when the wizard runs."""
        pr = self._create_approved_pr(with_work_supervisor=True)
        self.assertEqual(len(pr.work_acceptance_committee_ids), 1)
        self.assertEqual(len(pr.work_supervisor_ids), 1)

        po = self._make_purchase_order(pr)
        self.assertTrue(po, "A purchase order should have been created.")

        self.assertEqual(len(po.work_acceptance_committee_ids), 1)
        self.assertEqual(len(po.work_supervisor_ids), 1)

        wa = po.work_acceptance_committee_ids
        self.assertEqual(wa.employee_id, self.employee1)
        self.assertEqual(wa.committee_type, "work_acceptance")
        self.assertEqual(wa.approve_role, "chairman")

        ws = po.work_supervisor_ids
        self.assertEqual(ws.employee_id, self.employee2)
        self.assertEqual(ws.committee_type, "work_supervisor")

    def test_02_empty_work_supervisor_propagation(self):
        """PO gets empty work_supervisor_ids when PR has none."""
        pr = self._create_approved_pr(with_work_supervisor=False)
        self.assertEqual(len(pr.work_supervisor_ids), 0)

        po = self._make_purchase_order(pr)
        self.assertEqual(len(po.work_acceptance_committee_ids), 1)
        self.assertEqual(len(po.work_supervisor_ids), 0)

    def test_03_purchase_order_id_cascade(self):
        """Deleting a PO cascades to its linked procurement.committee records."""
        po = self.env["purchase.order"].create(
            {"partner_id": self.partner.id, "department_id": self.department.id}
        )
        committee = self.committee_model.create(
            {
                "name": self.employee1.display_name,
                "employee_id": self.employee1.id,
                "approve_role": "chairman",
                "committee_type": "work_acceptance",
                "purchase_order_id": po.id,
            }
        )
        committee_id = committee.id
        po.button_cancel()
        po.unlink()
        self.assertFalse(
            self.committee_model.browse(committee_id).exists(),
            "Committee should be deleted when linked PO is deleted.",
        )
