# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Tests for the invoice-plan features merged into purchase_work_acceptance_kmitl.

Covers the content absorbed from the former
purchase_work_acceptance_invoice_plan_usability (purchase.invoice.plan.wa_id /
wa_state) and purchase_work_acceptance_invoice_plan_deliverables
(purchase.invoice.plan.deliverables + work.acceptance.deliverables) modules.
"""

from odoo import Command, fields
from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWorkAcceptanceInvoicePlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Enable Work Acceptance on purchase orders
        cls.env["res.config.settings"].create(
            {
                "group_enable_wa_on_po": True,
                "group_enable_wa_on_in": True,
                "group_enable_wa_on_invoice": True,
            }
        ).execute()
        cls.partner = cls.env.ref("base.res_partner_12")
        cls.product = cls.env.ref("product.product_product_7")
        cls.product.purchase_method = "purchase"
        cls.apply_all = cls.env.ref(
            "purchase_work_acceptance_invoice_plan.apply_on_all_product_line"
        )
        # A confirmed PO with a 2-installment invoice plan, plus one draft WA
        # created for the first installment.
        cls.po = cls._create_po_with_invoice_plan()
        cls.installment = cls.po.invoice_plan_ids[0]
        cls.wa = cls._create_wa(cls.installment)

    @classmethod
    def _create_po_with_invoice_plan(cls):
        po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "use_invoice_plan": True,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom": cls.product.uom_id.id,
                            "name": cls.product.name,
                            "price_unit": 100.0,
                            "date_planned": fields.Datetime.now(),
                            "product_qty": 10,
                        }
                    )
                ],
            }
        )
        ctx = {"active_id": po.id, "active_ids": [po.id]}
        plan_form = Form(cls.env["purchase.create.invoice.plan"])
        plan_form.num_installment = 2
        plan = plan_form.save()
        plan.with_context(**ctx).purchase_create_invoice_plan()
        po.button_confirm()
        return po

    @classmethod
    def _create_wa(cls, installment):
        """Create a draft work acceptance for the given installment, mirroring
        the standard "Create WA by Installment" wizard flow."""
        po = installment.purchase_id
        ctx = {"active_id": po.id, "active_ids": [po.id]}
        with Form(
            cls.env["select.work.acceptance.invoice.plan.wizard"].with_context(**ctx)
        ) as wiz_form:
            wiz_form.installment_id = installment
            wiz_form.apply_method_id = cls.apply_all
        wizard = wiz_form.save()
        res = wizard.button_create_wa()
        return cls.env["work.acceptance"].with_context(**res["context"]).create({})

    # ------------------------------------------------------------------
    # deliverables (merged from ..._deliverables)
    # ------------------------------------------------------------------
    def test_invoice_plan_deliverables_stored(self):
        """purchase.invoice.plan.deliverables is a writable, stored Text field."""
        self.installment.deliverables = "งวดที่ 1: ส่งมอบรายงานการออกแบบ"
        self.installment.invalidate_recordset(["deliverables"])
        self.assertEqual(
            self.installment.deliverables, "งวดที่ 1: ส่งมอบรายงานการออกแบบ"
        )

    def test_work_acceptance_deliverables_related(self):
        """work.acceptance.deliverables mirrors its installment's deliverables."""
        field = self.env["work.acceptance"]._fields["deliverables"]
        self.assertEqual(field.related, "installment_id.deliverables")
        self.assertTrue(field.readonly)
        self.assertFalse(field.store)

        self.installment.deliverables = "ส่งมอบเฟส 1"
        self.wa.invalidate_recordset(["deliverables"])
        self.assertEqual(self.wa.deliverables, "ส่งมอบเฟส 1")

        # The relation is live: updating the installment reflects on the WA.
        self.installment.deliverables = "ส่งมอบเฟส 1 (แก้ไข)"
        self.wa.invalidate_recordset(["deliverables"])
        self.assertEqual(self.wa.deliverables, "ส่งมอบเฟส 1 (แก้ไข)")

    # ------------------------------------------------------------------
    # wa_id / wa_state (merged from ..._usability)
    # ------------------------------------------------------------------
    def test_invoice_plan_wa_reference_draft(self):
        """An installment points to its (latest, non-cancelled) WA and status."""
        self.installment.invalidate_recordset(["wa_id", "wa_state"])
        self.assertEqual(self.installment.wa_id, self.wa)
        self.assertEqual(self.installment.wa_state, "draft")

    def test_invoice_plan_wa_status_accept(self):
        """Accepting the WA propagates to the installment's wa_state."""
        self.wa.with_context(skip_committee_wizard=True).button_accept(
            force=fields.Datetime.now()
        )
        self.assertEqual(self.wa.state, "accept")
        self.installment.invalidate_recordset(["wa_id", "wa_state"])
        self.assertEqual(self.installment.wa_id, self.wa)
        self.assertEqual(self.installment.wa_state, "accept")

    def test_invoice_plan_wa_reference_excludes_cancelled(self):
        """A cancelled WA must not be reported as the installment's WA."""
        self.wa.button_cancel()
        self.assertEqual(self.wa.state, "cancel")
        self.installment.invalidate_recordset(["wa_id", "wa_state"])
        self.assertFalse(self.installment.wa_id)
        self.assertFalse(self.installment.wa_state)
