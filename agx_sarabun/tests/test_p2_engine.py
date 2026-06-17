# -*- coding: utf-8 -*-
"""P2 — routing engine: stages, dispositions, lifecycle, snapshot immutability."""
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP2Engine(SarabunCommon):
    # ----------------------------------------------------------------- stages
    def test_acknowledge_step_never_blocks_completion(self):
        """An acknowledge step in a stage doesn't stop the gating step completing it."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        ack = self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                             user=self.user_b)
        doc.action_send()
        self.assertTrue(doc.is_circulating)
        self.assertEqual(self.env["sarabun.routing.step"].browse(ack.id).state, "active")
        endorse = doc.routing_step_ids.filtered(lambda s: s.verb == "endorse")
        with self.mute_pdf():
            self._act(endorse, "complete", self.user_a)
        self.assertTrue(doc.is_completed)  # acknowledge still pending, did not block

    def test_sequential_stages_advance_in_order(self):
        """Stage 20 only activates once stage 10's gating is done."""
        doc = self._make_doc()
        s10 = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        s20 = self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self.assertEqual(s10.state, "active")
        self.assertEqual(s20.state, "waiting")
        self._act(s10, "complete", self.user_a)
        self.assertEqual(s20.state, "active")
        with self.mute_pdf():
            self._act(s20, "complete", self.user_b)
        self.assertTrue(doc.is_completed)

    def test_first_to_act_wins_on_multi_holder(self):
        """A multi-holder Position step is settled by the first holder to act."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="sign_approve",
                              target_mode="position", position=self.pos_multi)
        doc.action_send()
        self.assertEqual(step.actor_user_ids, self.user_a | self.user_b)
        with self.mute_pdf():
            self._act(step, "complete", self.user_a)
        self.assertEqual(step.state, "done")
        self.assertEqual(step.acted_by_id, self.user_a)
        # the other holder can no longer act — the step is settled
        with self.assertRaises(UserError):
            self._act(step, "complete", self.user_b)

    def test_one_reject_rejects_whole_document(self):
        """One reject in a co-approval stage rejects the document immediately."""
        doc = self._make_doc()
        s1 = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        s2 = self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self._act(s1, "reject", self.user_a, note="ไม่เห็นชอบ")
        self.assertTrue(doc.is_rejected)
        self.assertEqual(s2.state, "skipped")

    # ----------------------------------------------------------- dispositions
    def test_direct_inserts_next_step(self):
        """เกษียนสั่งการ completes this step and INSERTS the next one at order+1."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        doc.action_send()
        before = len(doc.routing_step_ids)
        self._act(step, "direct", self.user_a, note="มอบ ผอ. ดำเนินการ",
                  verb="sign_approve", target_mode="person", user_id=self.user_b.id)
        self.assertEqual(step.state, "done")
        self.assertEqual(step.disposition, "direct")
        self.assertEqual(len(doc.routing_step_ids), before + 1)
        inserted = doc.routing_step_ids.filtered(
            lambda s: s.created_by_disposition == "direct"
        )
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted.order, 11)
        self.assertEqual(inserted.inserted_by_step_id, step)
        self.assertTrue(doc.is_circulating)

    def test_delegate_reassigns_this_step_and_stays_active(self):
        """มอบหมาย reassigns THIS step to another actor; the step stays active."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        doc.action_send()
        before = len(doc.routing_step_ids)
        self._act(step, "delegate", self.user_a, note="มอบ ก ดำเนินการแทน",
                  target_mode="person", user_id=self.user_b.id)
        self.assertEqual(len(doc.routing_step_ids), before)  # no new step (unlike direct)
        self.assertEqual(step.state, "active")               # still active (unlike direct)
        self.assertIn(self.user_b, step.actor_user_ids)
        self.assertNotIn(self.user_a, step.actor_user_ids)

    def test_delegate_is_distinct_from_direct(self):
        """Delegate ≠ Direct: one reassigns in place, the other inserts a step."""
        doc_d = self._make_doc()
        s_d = self._add_step(doc_d, order=10, verb="endorse", user=self.user_a)
        doc_d.action_send()
        n0 = len(doc_d.routing_step_ids)
        self._act(s_d, "delegate", self.user_a, target_mode="person", user_id=self.user_b.id)
        self.assertEqual(len(doc_d.routing_step_ids), n0)
        self.assertEqual(s_d.state, "active")

        doc_i = self._make_doc()
        s_i = self._add_step(doc_i, order=10, verb="endorse", user=self.user_a)
        doc_i.action_send()
        m0 = len(doc_i.routing_step_ids)
        self._act(s_i, "direct", self.user_a, target_mode="person", user_id=self.user_b.id)
        self.assertEqual(len(doc_i.routing_step_ids), m0 + 1)
        self.assertEqual(s_i.state, "done")

    # --------------------------------------------------------- negative paths
    def test_return_sender_restart(self):
        """ตีกลับ (sender_restart) sends the doc back and bumps the attempt."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        doc.action_send()
        self.assertEqual(doc.attempt_seq, 1)
        self._act(step, "return", self.user_a, note="แก้เนื้อหา",
                  destination="sender_restart")
        self.assertTrue(doc.is_returned)
        self.assertEqual(doc.attempt_seq, 2)

    def test_return_resume_step(self):
        """ตีกลับ (resume_step) resets steps from the chosen order back to waiting."""
        doc = self._make_doc()
        s10 = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        s20 = self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self._act(s10, "complete", self.user_a)  # s20 now active
        self._act(s20, "return", self.user_b, destination="resume_step",
                  resume_step_id=s10.id)
        self.assertTrue(doc.is_returned)
        self.assertEqual(s10.state, "waiting")
        self.assertFalse(s10.disposition)

    def test_rejected_then_duplicate_to_draft(self):
        """rejected is terminal; retry is a NEW linked draft (1:N)."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self._act(step, "reject", self.user_a)
        self.assertTrue(doc.is_rejected)
        action = doc.action_duplicate_to_draft()
        new_doc = self.Doc.browse(action["res_id"])
        self.assertNotEqual(new_doc, doc)
        self.assertTrue(new_doc.is_draft)
        self.assertEqual(new_doc.attempt_seq, 1)
        self.assertTrue(doc.is_rejected)  # original preserved for audit

    def test_recall_before_signature_ok(self):
        """เรียกคืน is allowed while circulating and before any signature."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        doc.action_recall()
        self.assertTrue(doc.is_cancelled)

    def test_recall_blocked_after_signature(self):
        """Once a ลงนาม-อนุมัติ step is done, recall is blocked."""
        doc = self._make_doc()
        s10 = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self._act(s10, "complete", self.user_a)  # signed; stage 20 now active
        self.assertTrue(doc.has_signed)
        self.assertTrue(doc.is_circulating)
        with self.assertRaises(UserError):
            doc.action_recall()

    def test_snapshot_holders_are_immutable(self):
        """Holders snapshotted at activation are not rewritten by later org changes."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="sign_approve",
                              target_mode="position", position=self.pos)
        doc.action_send()
        self.assertEqual(step.actor_user_ids, self.user_a)
        self.pos.holder_ids = [(4, self.user_b.id)]  # org change after activation
        self.assertEqual(step.actor_user_ids, self.user_a)  # unchanged

    def test_send_requires_a_gating_step(self):
        """A document with no gating step cannot be sent."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.user_a)
        with self.assertRaises(UserError):
            doc.action_send()
