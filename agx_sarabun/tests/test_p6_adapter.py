# -*- coding: utf-8 -*-
"""P6 — integration adapter: 1:N link, step-carrying callbacks, atomic rollback, e2e."""
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP6Adapter(SarabunCommon):
    def _origin(self, name="PR ทดสอบ"):
        return self.Origin.create({"name": name, "test_department_id": self.dept.id})

    def _origin_doc(self, origin=None):
        origin = origin or self._origin()
        origin.action_create_sarabun_document()
        return origin, origin.active_sarabun_document_id

    def test_origin_spawns_and_links_document(self):
        """Creating from an origin spawns a linked หนังสือ exposed via the mixin."""
        origin, doc = self._origin_doc()
        self.assertTrue(doc)
        self.assertEqual(doc.origin_model, "test.sarabun.origin")
        self.assertEqual(doc.origin_res_id, origin.id)
        self.assertEqual(origin.sarabun_document_count, 1)
        self.assertEqual(origin.active_sarabun_document_id, doc)

    def test_callbacks_carry_a_routing_step(self):
        """Lifecycle callbacks fire in-transaction and carry a sarabun.routing.step."""
        origin, doc = self._origin_doc()
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertEqual(origin.circulating_count, 1)
        with self.mute_pdf():
            self._act(step, "complete", self.user_a)
        self.assertEqual(origin.completed_count, 1)
        self.assertGreaterEqual(origin.step_count, 1)
        self.assertTrue(origin.last_step_is_step)  # a routing.step, not the old recipient
        self.assertEqual(origin.last_disposition, "complete")

    def test_rejected_callback_reads_reason_from_step(self):
        """_on_sarabun_rejected(doc, step) reads the reason from the step outcome."""
        origin, doc = self._origin_doc()
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self._act(step, "reject", self.user_a, note="งบไม่พอ")
        self.assertEqual(origin.rejected_count, 1)
        self.assertEqual(origin.last_reject_note, "งบไม่พอ")

    def test_returned_callback(self):
        """ตีกลับ invokes _on_sarabun_returned(doc, step)."""
        origin, doc = self._origin_doc()
        step = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        doc.action_send()
        self._act(step, "return", self.user_a, destination="sender_restart")
        self.assertEqual(origin.returned_count, 1)

    def test_cancelled_callback(self):
        """เรียกคืน invokes _on_sarabun_cancelled(doc)."""
        origin, doc = self._origin_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        doc.action_recall()
        self.assertEqual(origin.cancelled_count, 1)

    def test_one_to_many_after_duplicate(self):
        """reject → duplicate-to-draft gives the origin a second linked document (1:N)."""
        origin, doc = self._origin_doc()
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self._act(step, "reject", self.user_a)
        action = doc.action_duplicate_to_draft()
        new_doc = self.Doc.browse(action["res_id"])
        self.assertEqual(origin.sarabun_document_count, 2)
        # the active one is the live (non-terminal) document
        self.assertEqual(origin.active_sarabun_document_id, new_doc)

    def test_callback_failure_rolls_back_the_action(self):
        """A raising origin callback rolls back the actor's disposition (atomic, no swallow)."""
        origin = self._origin()
        origin.raise_on_completed = True
        _, doc = self._origin_doc(origin)
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        with self.assertRaises(UserError), self.cr.savepoint():
            with self.mute_pdf():
                self._act(step, "complete", self.user_a)
        doc.invalidate_recordset()
        step.invalidate_recordset()
        self.assertEqual(doc.state, "circulating")   # NOT completed
        self.assertNotEqual(step.state, "done")
        self.assertEqual(origin.completed_count, 0)

    def test_end_to_end_via_origin(self):
        """Full e-flow: origin → endorse → sign-approve → completed → origin notified."""
        origin, doc = self._origin_doc()
        s_endorse = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        s_sign = self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self.assertTrue(doc.is_circulating)
        self._act(s_endorse, "complete", self.user_a)
        with self.mute_pdf():
            self._act(s_sign, "complete", self.user_b)
        self.assertTrue(doc.is_completed)
        self.assertEqual(origin.completed_count, 1)

    def test_has_live_document_gates_recreate(self):
        """sarabun_has_live_document drops to False once the only doc is terminal —
        so the consumer's 'create หนังสือ' button can reappear after reject/cancel."""
        origin, doc = self._origin_doc()
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertTrue(origin.sarabun_has_live_document)   # circulating = live → button hidden
        self._act(step, "reject", self.user_a)
        self.assertFalse(origin.sarabun_has_live_document)  # rejected = not live → button returns
        # a returned doc, by contrast, stays live (revised in place, not re-created)
        origin2, doc2 = self._origin_doc(self.Origin.create({"name": "PR2", "test_department_id": self.dept.id}))
        step2 = self._add_step(doc2, order=10, verb="endorse", user=self.user_a)
        doc2.action_send()
        self._act(step2, "return", self.user_a, destination="sender_restart")
        self.assertTrue(doc2.is_returned)
        self.assertTrue(origin2.sarabun_has_live_document)  # returned is NOT terminal → still live
