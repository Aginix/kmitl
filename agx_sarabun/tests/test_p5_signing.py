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

    def test_signature_and_kasian_trail(self):
        """_signature_steps = the sign step; the เกษียน trail = endorse + sign."""
        doc = self._make_doc()
        s_endorse = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        s_sign = self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self._act(s_endorse, "complete", self.user_a)
        with self.mute_pdf():
            self._act(s_sign, "complete", self.user_b)
        self.assertEqual(doc._signature_steps(), s_sign)
        self.assertEqual(doc._kasian_trail_steps(), s_endorse | s_sign)

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
