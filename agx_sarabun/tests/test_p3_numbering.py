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

    def _complete(self, doc, user=None):
        """Send then positively complete the single gating step → the number runs
        at completion (ADR-0010). PDF freeze is muted (no wkhtmltopdf in tests)."""
        doc.action_send()
        step = doc.routing_step_ids.filtered("gating")[:1]
        with self.mute_pdf():
            self._act(step, "complete", user or self.user_a)

    def test_number_not_assigned_until_completion(self):
        """No number while circulating — ที่ stays '/' until the final ลงนาม/อนุมัติ."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertFalse(doc.register_number_id)  # circulating, not yet numbered
        self.assertEqual(doc.name, "/")
        step = doc.routing_step_ids.filtered("gating")[:1]
        with self.mute_pdf():
            self._act(step, "complete", self.user_a)
        self.assertTrue(doc.is_completed)
        self.assertTrue(doc.register_number_id)  # numbered now
        self.assertNotEqual(doc.name, "/")

    def test_sequential_allocation_no_duplicate(self):
        """Two completed documents from one register get distinct, incrementing
        numbers (allocation happens at completion, in completion order)."""
        doc1 = self._make_doc()
        self._add_step(doc1, order=10, verb="sign_approve", user=self.user_a)
        self._complete(doc1)
        doc2 = self._make_doc()
        self._add_step(doc2, order=10, verb="sign_approve", user=self.user_a)
        self._complete(doc2)
        self.assertTrue(doc1.register_number_id)
        self.assertTrue(doc2.register_number_id)
        self.assertNotEqual(doc1.register_number_id, doc2.register_number_id)
        self.assertEqual(
            doc2.register_number_id.counter, doc1.register_number_id.counter + 1
        )
        self.assertNotEqual(doc1.name, doc2.name)
        # NOTE: true thread-concurrency races need a live multi-cursor DB; the
        # unique(sequence_id, counter, fiscal_year) constraint is the hard backstop.

    def test_rejected_document_consumes_no_number(self):
        """A rejected document never got a number (ADR-0010) — no wasted counter, so
        the next document to complete takes the next number with no gap."""
        doc1 = self._make_doc()
        self._add_step(doc1, order=10, verb="sign_approve", user=self.user_a)
        doc1.action_send()
        step = doc1.routing_step_ids.filtered("gating")[:1]
        self._act(step, "reject", self.user_a)
        self.assertFalse(doc1.register_number_id)  # never numbered
        self.assertEqual(doc1.name, "/")

        doc2 = self._make_doc()
        self._add_step(doc2, order=10, verb="sign_approve", user=self.user_a)
        self._complete(doc2)
        self.assertEqual(doc2.register_number_id.counter, 1)  # no gap consumed

    def test_cancelled_send_consumes_no_number(self):
        """ยกเลิกการส่ง on a circulating (unnumbered) document leaves no number."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        doc.action_recall(reason="ยกเลิกการส่ง")
        self.assertFalse(doc.register_number_id)
        self.assertEqual(doc.name, "/")

    # ------------------------------------------------ เล่มทะเบียน (ADR-0012)
    def _second_register(self):
        """A second เล่มทะเบียน for the same ส่วนงาน."""
        return self.Sequence.create({
            "name": "ทะเบียนหนังสือเวียน กองทดสอบ",
            "sender_department_id": self.dept.id,
            "prefix": "ว ",
        })

    def test_duplicate_register_is_distinguishable(self):
        """Duplicating a เล่มทะเบียน suffixes its name — the unit's books are told
        apart by name alone now that ``code`` is gone."""
        copy = self.sequence.copy()
        self.assertNotEqual(copy.name, self.sequence.name)
        self.assertIn(self.sequence.name, copy.name)
        self.assertEqual(copy.sender_department_id, self.dept)

    def test_single_register_is_picked_without_choosing(self):
        """A unit with one register needs no choice — the หนังสือ defaults to it."""
        doc = self._make_doc()
        self.assertEqual(doc.sequence_id, self.sequence)

    def test_unit_default_register_wins_when_several_exist(self):
        """หลายเล่ม + เล่มทะเบียนหลัก set on the unit → new หนังสือ default to it."""
        second = self._second_register()
        self.dept.default_sarabun_sequence_id = second
        doc = self._make_doc()
        self.assertEqual(doc.sequence_id, second)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._complete(doc)
        self.assertEqual(doc.register_number_id.sequence_id, second)

    def test_chosen_register_book_issues_the_number(self):
        """The book chosen on the หนังสือ overrides the unit's default."""
        second = self._second_register()
        self.dept.default_sarabun_sequence_id = self.sequence
        doc = self._make_doc()
        doc.sequence_id = second
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._complete(doc)
        self.assertEqual(doc.register_number_id.sequence_id, second)
        self.assertTrue(doc.name.startswith("ว "))

    def test_ambiguous_register_blocks_send(self):
        """Several books and no default → the sender must pick one; send is blocked."""
        self._second_register()
        doc = self._make_doc()
        self.assertFalse(doc.sequence_id)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        with self.assertRaises(UserError):
            doc.action_send()

    def test_register_book_is_pinned_at_send(self):
        """The resolved book is pinned at ส่ง, so a later config change can't move the
        หนังสือ to another book before ลงทะเบียน runs at completion."""
        self.dept.default_sarabun_sequence_id = self.sequence
        doc = self._make_doc()
        doc.sequence_id = False  # a หนังสือ that never picked a book (falls back)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertEqual(doc.sequence_id, self.sequence)  # pinned at ส่ง
        second = self._second_register()
        self.dept.default_sarabun_sequence_id = second  # unit switches books mid-route
        step = doc.routing_step_ids.filtered("gating")[:1]
        with self.mute_pdf():
            self._act(step, "complete", self.user_a)
        self.assertEqual(doc.register_number_id.sequence_id, self.sequence)

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
        self._complete(doc)
        number = doc.register_number_id
        padded = str(number.counter).zfill(self.sequence.padding)
        self.assertIn(padded, number.register_number)
        self.assertIn(str(number.fiscal_year), number.register_number)
        self.assertEqual(doc.name, number.register_number)
