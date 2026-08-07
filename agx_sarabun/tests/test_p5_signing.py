# -*- coding: utf-8 -*-
"""P5 — signing: freeze on completion, signature/เกษียน trail, capacity validation."""
import base64

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP5Signing(SarabunCommon):
    def _complete_single_sign(self, doc, user=None):
        step = self._add_step(doc, order=10, verb="sign_approve", user=user or self.user_a)
        doc.action_send()
        with self.mute_pdf():
            self._act(step, "complete", user or self.user_a)
        return step

    def test_freeze_on_completion(self):
        """At completed the official PDF is frozen as an immutable attachment."""
        doc = self._make_doc()
        self.assertFalse(doc.is_frozen)
        self._complete_single_sign(doc)
        self.assertTrue(doc.is_completed)
        self.assertTrue(doc.is_frozen)
        self.assertTrue(doc.signed_at)
        self.assertTrue(doc.signed_pdf)

    def test_completion_attaches_visible_pdf(self):
        """At completion the approved PDF is dropped into the record's Attachments as a
        plain ir.attachment (res_field unset) — the signed_pdf Binary is res_field-backed
        and hidden from that list — so it shows in the หนังสือ's attachment box (feedback)."""
        doc = self._make_doc()
        self._complete_single_sign(doc)
        atts = self.env["ir.attachment"].search([
            ("res_model", "=", "sarabun.document"),
            ("res_id", "=", doc.id),
            ("res_field", "=", False),
        ])
        self.assertIn(doc.signed_pdf_filename, atts.mapped("name"))

    def test_signature_block_and_trail_semantics(self):
        """ADR-0008 three axes. _signature_steps = the authoritative sign only
        (is_signature — the originator is no longer is_signature). _signature_block_steps
        = every RENDERED signature (show_signature: the signing ผู้จัดทำ + เห็นชอบ +
        ลงนาม-อนุมัติ). _kasian_trail_steps = the audit trail (gating), NOT rendered on
        the document."""
        doc = self._make_doc()
        originator = doc.routing_step_ids.filtered("is_originator")
        s_endorse = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        s_sign = self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self._act(s_endorse, "complete", self.user_a)
        with self.mute_pdf():
            self._act(s_sign, "complete", self.user_b)
        # Authoritative sign = the ลงนาม-อนุมัติ step only.
        self.assertEqual(doc._signature_steps(), s_sign)
        # Rendered signatures = show_signature steps: signing ผู้จัดทำ + เห็นชอบ + ลงนาม.
        self.assertEqual(doc._signature_block_steps(), originator | s_endorse | s_sign)
        # Audit trail (gating) — endorse + sign; not printed on the document.
        self.assertEqual(doc._kasian_trail_steps(), s_endorse | s_sign)

    def test_nonsigning_drafter_shows_no_signature(self):
        """ADR-0008: a เจ้าหน้าที่ธุรการ may ร่าง without signing — the originator carries
        the non-signing จัดทำ/ร่าง verb, so their name is in the Route but NO signature
        renders; the หัวหน้าส่วนงาน's ลงนาม-อนุมัติ is the only signature, and the sender
        may still ดึงกลับ (has_signed False) until it happens."""
        doc = self._make_doc()
        originator = doc.routing_step_ids.filtered("is_originator")
        originator.verb = self._verb("prepare")  # ธุรการร่าง — ไม่ลงนาม
        head = self._add_step(doc, order=10, verb="sign_approve",
                              target_mode="position", position=self.pos)
        doc.action_send()
        # Drafter auto-completed at send, but is not a signature; recall still open.
        self.assertEqual(originator.state, "done")
        self.assertNotIn(originator, doc._signature_block_steps())
        # A non-signing originator snapshots no signature identity (ADR-0009).
        self.assertFalse(originator.signed_name)
        self.assertFalse(originator.signed_signature)
        self.assertFalse(doc.has_signed)
        # Head signs → the only signature on the document; the หนังสือ completes.
        with self.mute_pdf():
            self._act(head, "complete", self.user_a, signed_as_position_id=self.pos.id)
        self.assertTrue(doc.is_completed)
        self.assertTrue(doc.has_signed)
        self.assertEqual(doc._signature_block_steps(), head)

    def test_get_official_pdf_serves_frozen_bytes(self):
        """Once frozen, _get_official_pdf returns the stored bytes (no live render)."""
        doc = self._make_doc()
        self._complete_single_sign(doc)
        self.assertEqual(doc._get_official_pdf(), b"%PDF-1.4 test")
        self.assertEqual(base64.b64decode(doc.signed_pdf), b"%PDF-1.4 test")

    def test_freeze_is_idempotent(self):
        """Re-freezing a completed doc is a no-op (one-way)."""
        doc = self._make_doc()
        self._complete_single_sign(doc)
        first_at = doc.signed_at
        doc._freeze_signed_copy()  # guard returns early; no render needed
        self.assertEqual(doc.signed_at, first_at)

    def test_sign_capacity_must_match_step_position(self):
        """A Position sign step must be signed in the capacity it targets (ADR-0003)."""
        doc = self._make_doc()
        step = self._add_step(doc, order=10, verb="sign_approve",
                              target_mode="position", position=self.pos)
        doc.action_send()
        with self.assertRaises(UserError):
            self._act(step, "complete", self.user_a,
                      signed_as_position_id=self.pos_multi.id)  # wrong capacity
        with self.mute_pdf():
            self._act(step, "complete", self.user_a, signed_as_position_id=self.pos.id)
        self.assertEqual(step.signed_as_position_id, self.pos)
        self.assertTrue(doc.is_completed)

    def test_signature_snapshot_frozen_against_source_edits(self):
        """ADR-0009: ชื่อ / ตำแหน่ง / ลายเซ็น are snapshotted at signing, so later edits to
        the HR name, the Position name, or the employee's signature image never rewrite
        an already-signed step (on any render path — PDF, preview, direct-origin print)."""
        self.emp_a.signature = base64.b64encode(b"signature-v1")
        doc = self._make_doc(sender=self.user_a)
        originator = doc.routing_step_ids.filtered("is_originator")
        step = self._add_step(doc, order=10, verb="sign_approve",
                              target_mode="position", position=self.pos)
        doc.action_send()  # auto-signs the originator (ลงนามผู้จัดทำ, show_signature)
        with self.mute_pdf():
            self._act(step, "complete", self.user_a, signed_as_position_id=self.pos.id)

        # Captured at signing: name + capacity + the signature image bytes.
        self.assertEqual(step.signed_name, "ผู้ใช้ ก")
        self.assertEqual(step.signed_position_name, "คณบดีทดสอบ")
        frozen_sig = step.signed_signature
        self.assertTrue(frozen_sig)
        # The signing ผู้จัดทำ (originator) is snapshotted too, at send.
        self.assertEqual(originator.signed_name, "ผู้ใช้ ก")

        # Source master data drifts AFTER signing …
        self.emp_a.name = "ผู้ใช้ ก (แก้ชื่อ)"
        self.pos.name = "ตำแหน่งใหม่หลังลงนาม"
        self.emp_a.signature = base64.b64encode(b"signature-v2")

        # … the frozen snapshot on the signed step is unchanged.
        self.assertEqual(step.signed_name, "ผู้ใช้ ก")
        self.assertEqual(step.signed_position_name, "คณบดีทดสอบ")
        self.assertEqual(step.signed_signature, frozen_sig)
        self.assertNotEqual(step.signed_signature, self.emp_a.signature)
