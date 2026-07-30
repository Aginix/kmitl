# -*- coding: utf-8 -*-
"""Admin reset-to-draft (ADR-0011) — behaviour of ``action_reset_to_draft``.

Reuses agx_sarabun's SarabunCommon fixtures + spy origin; adds a reset-admin user.
Covers reset from completed / rejected / circulating, the guards (draft, non-admin,
empty reason), number keep/reclaim, un-freeze, the ``_on_sarabun_recalled`` origin
rollback, and re-send on the same number.
"""
from odoo.exceptions import UserError
from odoo.tests.common import new_test_user, tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestSarabunReset(SarabunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reset_user = new_test_user(
            cls.env, login="sb_reset", name="ผู้รีเซ็ต",
            groups="base.group_user,agx_sarabun_reset.group_sarabun_reset",
        )
        # An employee so reset_user's has_group / route reads are ordinary.
        cls.env["hr.employee"].create({"name": "ผู้รีเซ็ต", "user_id": cls.reset_user.id})

    # ------------------------------------------------------------------ helpers
    def _make_origin(self):
        return self.Origin.create({"name": "src", "test_department_id": self.dept.id})

    def _complete_doc(self, origin=None, with_insertion=False):
        """Build → send → complete a simple one-gating-step หนังสือ. When
        ``with_insertion`` is set, the signer เกษียนสั่งการ (direct) a follow-up
        acknowledge step before completion, so the reset has a 'direct' insertion to
        drop."""
        doc = self._make_doc(sender=self.user_a, origin=origin)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person",
                       user=self.user_a)
        with self.mute_pdf():
            doc.action_send()
            step = self._active_step(doc)
            if with_insertion:
                self._act(step, "direct", self.user_a, verb=self._verb("acknowledge").id,
                          target_mode="person", employee_id=self.emp_b.id)
            else:
                self._act(step, "complete", self.user_a)
        return doc

    def _reset(self, doc, reason="typo", user=None):
        return doc.with_user(user or self.reset_user).action_reset_to_draft(reason)

    # ------------------------------------------------------------------ tests
    def test_reset_from_completed(self):
        """Reset a completed หนังสือ: seed-only route (insertion dropped), number kept,
        un-frozen, origin rolled back, back to draft — then re-send on the same number."""
        origin = self._make_origin()
        doc = self._complete_doc(origin=origin, with_insertion=True)
        self.assertEqual(doc.state, "completed")
        self.assertTrue(doc.is_frozen)
        number = doc.register_number_id
        original_name = doc.name
        self.assertTrue(doc.routing_step_ids.filtered(
            lambda s: s.created_by_disposition == "direct"))

        self._reset(doc, reason="แก้คำผิด")

        # state + number
        self.assertEqual(doc.state, "draft")
        self.assertEqual(doc.name, original_name, "number kept")
        self.assertEqual(doc.register_number_id, number)
        self.assertEqual(number.state, "used")
        # route = seed backbone only; the เกษียนสั่งการ insertion is dropped
        self.assertFalse(doc.routing_step_ids.filtered(
            lambda s: s.created_by_disposition == "direct"), "insertion dropped")
        gating = doc.routing_step_ids.filtered("gating")
        self.assertEqual(len(gating), 1)
        self.assertTrue(all(s.state == "waiting" for s in doc.routing_step_ids))
        self.assertTrue(doc.routing_step_ids.filtered("is_originator"))
        # finished attempt archived as history
        self.assertTrue(doc.archived_step_ids)
        self.assertEqual(doc.attempt_seq, 2)
        # un-frozen
        self.assertFalse(doc.is_frozen)
        self.assertFalse(doc.signed_pdf)
        self.assertFalse(doc.signed_at)
        # origin rolled back like ดึงกลับ
        self.assertEqual(origin.recalled_count, 1)

        # re-send works on the same number
        with self.mute_pdf():
            doc.action_send()
        self.assertEqual(doc.state, "circulating")
        self.assertEqual(doc.name, original_name)
        self.assertEqual(doc.register_number_id, number)

    def test_reset_from_rejected_unvoids_number(self):
        """Reset out of rejected reclaims the voided number (voided → used)."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person",
                       user=self.user_a)
        with self.mute_pdf():
            doc.action_send()
            step = self._active_step(doc)
            self._act(step, "reject", self.user_a, note="ไม่ผ่าน")
        self.assertEqual(doc.state, "rejected")
        number = doc.register_number_id
        self.assertEqual(number.state, "voided")

        self._reset(doc, reason="กู้เรื่อง")

        self.assertEqual(doc.state, "draft")
        self.assertEqual(number.state, "used", "voided → used")
        self.assertFalse(number.void_reason)
        self.assertFalse(number.void_date)
        self.assertEqual(doc.register_number_id, number)

    def test_reset_from_cancelled_unvoids_number(self):
        """Reset out of cancelled (ยกเลิกการส่ง) reclaims the voided number too."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person",
                       user=self.user_a)
        with self.mute_pdf():
            doc.action_send()
        doc.action_recall("ส่งผิด")
        self.assertEqual(doc.state, "cancelled")
        number = doc.register_number_id
        self.assertEqual(number.state, "voided")

        self._reset(doc, reason="กู้เรื่อง")

        self.assertEqual(doc.state, "draft")
        self.assertEqual(number.state, "used")
        self.assertFalse(number.void_reason)

    def test_reset_from_circulating(self):
        """Reset a mid-flight หนังสือ: back to draft, seed route re-created, number kept."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person",
                       user=self.user_a)
        with self.mute_pdf():
            doc.action_send()
        self.assertEqual(doc.state, "circulating")
        number = doc.register_number_id

        self._reset(doc, reason="รีเซ็ต")

        self.assertEqual(doc.state, "draft")
        self.assertEqual(doc.register_number_id, number)
        self.assertEqual(number.state, "used")
        self.assertTrue(doc.archived_step_ids)
        self.assertTrue(all(s.state == "waiting" for s in doc.routing_step_ids))

    def test_reset_blocked_from_draft(self):
        doc = self._make_doc(sender=self.user_a)
        with self.assertRaises(UserError):
            self._reset(doc, reason="x")

    def test_reset_blocked_for_non_admin(self):
        doc = self._complete_doc()
        with self.assertRaises(UserError):
            self._reset(doc, reason="x", user=self.user_a)

    def test_reset_blocked_empty_reason(self):
        doc = self._complete_doc()
        with self.assertRaises(UserError):
            self._reset(doc, reason="")

    def test_can_reset_flag(self):
        """can_reset drives the button: True for a reset admin on a non-draft doc,
        False on a draft and False for a non-admin."""
        doc = self._complete_doc()
        self.assertTrue(doc.with_user(self.reset_user).can_reset)
        self.assertFalse(doc.with_user(self.user_a).can_reset)
        draft = self._make_doc(sender=self.user_a)
        self.assertFalse(draft.with_user(self.reset_user).can_reset)
