# -*- coding: utf-8 -*-
"""P3 — numbering / register: per-(unit×type) isolation, atomic allocate, voids, fiscal year."""
from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP3Numbering(SarabunCommon):
    def test_send_blocked_without_register(self):
        """Send is blocked (clear error) when no register exists for (unit × type)."""
        dept2 = self.env["hr.department"].create({"name": "กองไม่มีทะเบียน"})
        doc = self._make_doc(sender_department_id=dept2.id)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        with self.assertRaises(UserError):
            doc.action_send()

    def test_sequential_allocation_no_duplicate(self):
        """Two documents from one register get distinct, incrementing numbers."""
        doc1 = self._make_doc()
        self._add_step(doc1, order=10, verb="sign_approve", user=self.user_a)
        doc1.action_send()
        doc2 = self._make_doc()
        self._add_step(doc2, order=10, verb="sign_approve", user=self.user_a)
        doc2.action_send()
        self.assertTrue(doc1.register_number_id)
        self.assertTrue(doc2.register_number_id)
        self.assertNotEqual(doc1.register_number_id, doc2.register_number_id)
        self.assertEqual(
            doc2.register_number_id.counter, doc1.register_number_id.counter + 1
        )
        self.assertNotEqual(doc1.name, doc2.name)
        # NOTE: true thread-concurrency races need a live multi-cursor DB; the
        # unique(sequence_id, counter, fiscal_year) constraint is the hard backstop.

    def test_voided_number_is_a_permanent_gap(self):
        """A rejected document's number is voided and never reissued."""
        doc1 = self._make_doc()
        self._add_step(doc1, order=10, verb="sign_approve", user=self.user_a)
        doc1.action_send()
        n1 = doc1.register_number_id.counter
        step = doc1.routing_step_ids.filtered("gating")[:1]
        self._act(step, "reject", self.user_a)
        self.assertEqual(doc1.register_number_id.state, "voided")
        self.assertEqual(doc1.register_number_id.void_reason, "rejected")

        doc2 = self._make_doc()
        self._add_step(doc2, order=10, verb="sign_approve", user=self.user_a)
        doc2.action_send()
        self.assertEqual(doc2.register_number_id.counter, n1 + 1)  # gap, n1 not reused

    def test_recall_voids_number_as_cancelled(self):
        """ยกเลิกการส่ง voids the number with reason 'cancelled'."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        doc.action_recall(reason="ยกเลิกการส่ง")
        self.assertEqual(doc.register_number_id.state, "voided")
        self.assertEqual(doc.register_number_id.void_reason, "cancelled")

    def test_fiscal_year_bucket(self):
        """ปีงบประมาณ runs Oct–Sep; Oct–Dec roll into the next budget year (พ.ศ.)."""
        seq = self.sequence
        self.assertEqual(seq._fiscal_year_for(date(2025, 10, 1)), 2569)   # Oct 2025 → FY2569
        self.assertEqual(seq._fiscal_year_for(date(2026, 1, 15)), 2569)   # Jan 2026 → FY2569
        self.assertEqual(seq._fiscal_year_for(date(2026, 9, 30)), 2569)   # Sep 2026 → FY2569
        self.assertEqual(seq._fiscal_year_for(date(2025, 9, 30)), 2568)   # Sep 2025 → FY2568

    def test_register_number_rendering(self):
        """register_number is zero-padded to the register's width and carries the FY."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        number = doc.register_number_id
        padded = str(number.counter).zfill(self.sequence.padding)
        self.assertIn(padded, number.register_number)
        self.assertIn(str(number.fiscal_year), number.register_number)
        self.assertEqual(doc.name, number.register_number)
