# -*- coding: utf-8 -*-
"""P3 — numbering / register: per-(unit×type) isolation, atomic allocate, voids, fiscal year."""
from datetime import date

from odoo import fields
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
        """Send then positively complete the single gating (ลงนามในใบปะหน้า) step →
        the number runs at that sign (ADR-0017). PDF freeze is muted (no wkhtmltopdf
        in tests)."""
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

    # ------------------------------------- number at the issuing sign (ADR-0017)
    def _sign(self, doc, verb, user):
        """Positively complete the active step of ``verb`` as ``user``."""
        step = doc.routing_step_ids.filtered(
            lambda s: s.state == "active" and s.verb == self._verb(verb)
        )
        with self.mute_pdf():
            self._act(step, "complete", user)

    def test_number_issued_at_sign_not_completion(self):
        """The number runs when ลงนามในใบปะหน้า is signed, even with steps after it;
        completion keeps that same number."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        self._add_step(doc, order=30, verb="approve", user=self.user_a)
        doc.action_send()
        self._sign(doc, "endorse", self.user_a)
        self.assertFalse(doc.register_number_id)  # เห็นชอบ issues no number
        self._sign(doc, "sign_approve", self.user_b)
        number = doc.register_number_id
        self.assertTrue(number)
        self.assertTrue(doc.is_circulating)  # numbered while still circulating
        self.assertEqual(doc.name, number.register_number)
        self._sign(doc, "approve", self.user_a)
        self.assertTrue(doc.is_completed)
        self.assertEqual(doc.register_number_id, number)  # not re-numbered

    def test_first_issuing_sign_wins(self):
        """With several ลงนามในใบปะหน้า signers the first one issues the number."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self._sign(doc, "sign_approve", self.user_a)
        number = doc.register_number_id
        self.assertTrue(number)
        self._sign(doc, "sign_approve", self.user_b)
        self.assertTrue(doc.is_completed)
        self.assertEqual(doc.register_number_id, number)
        self.assertEqual(number.counter, 1)  # one number consumed

    def test_number_issued_at_sign_via_direct(self):
        """Signing ลงนามในใบปะหน้า via เกษียนสั่งการ (sign and forward) issues the
        number at that sign too."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self._act(step, "direct", self.user_a, note="เสนอ อธิการบดี",
                  verb=self._verb("approve").id, target_mode="person",
                  employee_id=self.emp_b.id)
        self.assertTrue(doc.register_number_id)
        self.assertTrue(doc.is_circulating)

    def test_send_blocked_without_issuing_step(self):
        """A route with no number-issuing step cannot be sent."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        with self.assertRaises(UserError):
            doc.action_send()

    def test_issuing_verb_is_configurable(self):
        """Ticking ออกเลขที่หนังสือ on another verb makes that step issue the number."""
        self._verb("approve").issues_number = True
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="approve", user=self.user_a)
        self._add_step(doc, order=20, verb="endorse", user=self.user_b)
        doc.action_send()
        self._sign(doc, "approve", self.user_a)
        self.assertTrue(doc.register_number_id)
        self.assertTrue(doc.is_circulating)

    def test_reject_after_issuing_sign_voids_number(self):
        """ปฏิเสธ after the number was issued voids it as a permanent gap."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._add_step(doc, order=20, verb="approve", user=self.user_b)
        doc.action_send()
        self._sign(doc, "sign_approve", self.user_a)
        number = doc.register_number_id
        step = self._active_step(doc)
        self._act(step, "reject", self.user_b, note="ไม่อนุมัติ")
        self.assertTrue(doc.is_rejected)
        self.assertEqual(number.state, "voided")

    def test_return_after_issuing_sign_keeps_number(self):
        """ตีกลับ after the number was issued keeps it; the re-sign reuses it."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._add_step(doc, order=20, verb="approve", user=self.user_b)
        doc.action_send()
        self._sign(doc, "sign_approve", self.user_a)
        number = doc.register_number_id
        self._act(self._active_step(doc), "return", self.user_b,
                  note="แก้ไข", destination="sender_restart")
        self.assertTrue(doc.is_returned)
        self.assertEqual(doc.register_number_id, number)
        doc.action_send()
        self._sign(doc, "sign_approve", self.user_a)
        self.assertEqual(doc.register_number_id, number)
        self.assertEqual(number.state, "used")

    def test_resend_numbered_without_issuing_step(self):
        """ตีกลับ→resume past the issuing sign leaves no issuing step in the new
        attempt; the numbered หนังสือ can still be re-sent and keeps its number,
        book and ลงวันที่."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._add_step(doc, order=20, verb="endorse", user=self.user_b)
        self._add_step(doc, order=30, verb="approve", user=self.user_a)
        doc.action_send()
        self._sign(doc, "sign_approve", self.user_a)
        self._sign(doc, "endorse", self.user_b)
        number, book = doc.register_number_id, doc.sequence_id
        resume = doc.routing_step_ids.filtered(lambda s: s.verb == self._verb("endorse"))
        self._act(self._active_step(doc), "return", self.user_a, note="แก้ไข",
                  destination="resume_step", resume_step_id=resume.id)
        self.assertFalse(doc.routing_step_ids.filtered("verb.issues_number"))
        doc.date = date(2020, 1, 1)
        doc.action_send()
        self.assertTrue(doc.is_circulating)
        self.assertEqual(doc.register_number_id, number)
        self.assertEqual(doc.sequence_id, book)
        self.assertEqual(doc.date, date(2020, 1, 1))  # not re-stamped at re-send

    def test_date_stamped_at_issuing_sign(self):
        """ลงวันที่ is empty until the number is issued, then that day."""
        doc = self._make_doc()
        self.assertFalse(doc.date)
        self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self.assertFalse(doc.date)  # sent, still unnumbered
        self._sign(doc, "endorse", self.user_a)
        self.assertFalse(doc.date)
        self._sign(doc, "sign_approve", self.user_b)
        self.assertEqual(doc.date, fields.Date.context_today(doc))

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

    def test_archived_book_not_used_at_send(self):
        """A draft still holding a book the unit retired (archive) must not issue from
        it: send falls back to the unit's active default instead of the stale pick."""
        second = self._second_register()
        doc = self._make_doc()
        self.assertEqual(doc.sequence_id, self.sequence)  # unit's only book at create
        self.dept.default_sarabun_sequence_id = second
        self.sequence.active = False  # the picked book is retired after the draft
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertEqual(doc.sequence_id, second)  # fell back to the active default
        step = doc.routing_step_ids.filtered("gating")[:1]
        with self.mute_pdf():
            self._act(step, "complete", self.user_a)
        self.assertEqual(doc.register_number_id.sequence_id, second)

    def test_calendar_year_bucket(self):
        """The register resets each calendar year (พ.ศ.); the month is irrelevant."""
        seq = self.sequence
        self.assertEqual(seq._fiscal_year_for(date(2025, 10, 1)), 2568)   # 2025 → 2568
        self.assertEqual(seq._fiscal_year_for(date(2025, 12, 31)), 2568)  # 2025 → 2568
        self.assertEqual(seq._fiscal_year_for(date(2026, 1, 15)), 2569)   # 2026 → 2569
        self.assertEqual(seq._fiscal_year_for(date(2026, 9, 30)), 2569)   # 2026 → 2569

    def test_register_number_rendering(self):
        """register_number is zero-padded to the register's width and carries NO ปีงบ
        (feedback: เลขที่หนังสือต้องไม่มีเลขปี — the running number omits the year)."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._complete(doc)
        number = doc.register_number_id
        padded = str(number.counter).zfill(self.sequence.padding)
        expected = "%s%s%s" % (
            self.sequence.prefix or "", padded, self.sequence.suffix or "",
        )
        self.assertEqual(number.register_number, expected)
        self.assertNotIn(str(number.fiscal_year), number.register_number)
        self.assertEqual(doc.name, number.register_number)
