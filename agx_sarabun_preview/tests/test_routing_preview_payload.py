# -*- coding: utf-8 -*-
"""Snapshot tests for the routing-timeline preview payload consumed by the
SarabunRoutingTimeline OWL widget (agx_sarabun_preview).

The payload contract must stay stable — a shape break silently blanks both the
form and wizard surfaces. These tests pin the shape end-to-end: grouping by
Stage, holder resolution (pre- vs post-activation), state/disposition mapping,
note truncation, and archived-attempt grouping."""
import json

from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestRoutingPreviewPayload(SarabunCommon):
    def _payload(self, doc):
        raw = doc.routing_preview_json
        self.assertTrue(raw, "routing_preview_json should never be empty")
        return json.loads(raw)

    # -- shape --------------------------------------------------------------

    def test_empty_document_payload_shape(self):
        """A draft with no seeded steps yields a well-formed empty payload."""
        doc = self._make_doc(sender=self.user_a)
        data = self._payload(doc)
        self.assertEqual(data["attempt_seq"], 1)
        self.assertFalse(data["has_history"])
        self.assertEqual(data["stages"], [])

    def test_draft_route_all_waiting(self):
        """A draft with seeded steps shows every step as waiting (no is_current)."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person", user=self.user_a)
        self._add_step(doc, order=20, verb="acknowledge", target_mode="person", user=self.user_b)
        data = self._payload(doc)
        self.assertEqual(len(data["stages"]), 2)
        for stage in data["stages"]:
            for step in stage["steps"]:
                self.assertEqual(step["state"], "waiting")
                self.assertFalse(step["is_current"])
                self.assertIsNone(step["acted_by"])

    def test_stages_group_parallel_steps(self):
        """Two steps sharing an order collapse into one Stage."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person", user=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person", user=self.user_b)
        self._add_step(doc, order=20, verb="acknowledge", target_mode="person", user=self.user_a)
        data = self._payload(doc)
        by_order = {s["order"]: s for s in data["stages"]}
        self.assertEqual(len(by_order[10]["steps"]), 2)
        self.assertEqual(len(by_order[20]["steps"]), 1)

    # -- holders ------------------------------------------------------------

    def test_multi_holder_position_pre_activation(self):
        """A Position with N holders shows every holder as a chip before activation."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="position", position=self.pos_multi)
        data = self._payload(doc)
        step = data["stages"][0]["steps"][0]
        holder_names = {h["name"] for h in step["holders"]}
        self.assertEqual(holder_names, {"ผู้ใช้ ก", "ผู้ใช้ ข"})

    # -- active + circulating -----------------------------------------------

    def test_circulating_active_step_marked_current(self):
        """After action_send the active step has is_current=True."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person", user=self.user_a)
        doc.with_user(self.user_a).action_send()
        active = self._active_step(doc)
        self.assertTrue(active)
        data = self._payload(doc)
        found = [
            step for stage in data["stages"] for step in stage["steps"]
            if step["id"] == active.id
        ]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["state"], "active")
        self.assertTrue(found[0]["is_current"])
        self.assertTrue(found[0]["activated_date"])

    def test_completed_step_records_acted_by(self):
        """A done+complete step carries acted_by name, acted_date, state=done."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person", user=self.user_a)
        self._add_step(doc, order=20, verb="acknowledge", target_mode="person", user=self.user_b)
        doc.with_user(self.user_a).action_send()
        active = self._active_step(doc)
        self._act(active, "complete", self.user_a)
        data = self._payload(doc)
        signed = [
            step for stage in data["stages"] for step in stage["steps"]
            if step["id"] == active.id
        ][0]
        self.assertEqual(signed["state"], "done")
        self.assertEqual(signed["disposition"], "complete")
        self.assertIsNotNone(signed["acted_by"])
        self.assertEqual(signed["acted_by"]["name"], "ผู้ใช้ ก")
        self.assertTrue(signed["acted_date"])

    # -- note truncation ----------------------------------------------------

    def test_note_truncation(self):
        """Notes longer than _PREVIEW_NOTE_MAX get note_short with ellipsis."""
        doc = self._make_doc(sender=self.user_a)
        step = self._add_step(doc, order=10, verb="acknowledge", target_mode="person", user=self.user_a)
        long_note = "ก" * 200
        step.note = long_note
        data = self._payload(doc)
        card = data["stages"][0]["steps"][0]
        self.assertEqual(card["note_full"], long_note)
        self.assertTrue(card["note_short"].endswith("…"))
        self.assertEqual(len(card["note_short"]), doc._PREVIEW_NOTE_MAX + 1)

    # -- attempt history ----------------------------------------------------

    def test_attempt_seq_and_history_flag(self):
        """After ตีกลับ, attempt_seq >= 2, has_history=True, archived payload non-empty."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person", user=self.user_a)
        self._add_step(doc, order=20, verb="sign_approve", target_mode="person", user=self.user_b)
        doc.with_user(self.user_a).action_send()
        first = self._active_step(doc)
        self._act(first, "complete", self.user_a)
        second = self._active_step(doc)
        self.assertTrue(second)
        self._act(second, "return", self.user_b, note="ขอแก้")
        data = self._payload(doc)
        self.assertGreaterEqual(data["attempt_seq"], 2)
        self.assertTrue(data["has_history"])
        history = doc._build_archived_attempts_payload()
        self.assertTrue(history)
        seqs = [a["attempt_seq"] for a in history]
        self.assertEqual(seqs, sorted(seqs, reverse=True))

    # -- action RPC ---------------------------------------------------------

    def test_action_open_routing_history_shape(self):
        """action_open_routing_history returns client-action tag + params.attempts."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="person", user=self.user_a)
        action = doc.action_open_routing_history()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "sarabun_routing_timeline_archive")
        self.assertIn("attempts", action["params"])
        self.assertEqual(action["params"]["doc_id"], doc.id)
