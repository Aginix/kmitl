"""P8 — 🔙 ดึงกลับ (take back): a route actor reopens their own step (ADR-0024)."""

import base64

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP8TakeBack(SarabunCommon):
    def _doc(self):
        """Sender manager; ลำดับ 10 endorse by user_a, ลำดับ 20 sign_approve by user_b."""
        self._verb("endorse").allow_sign_comment = True
        doc = self._make_doc(sender=self.manager)
        s10 = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        s20 = self._add_step(doc, order=20, verb="sign_approve", user=self.user_b)
        doc.action_send()
        return doc, s10, s20

    def _can_read(self, doc, user):
        return bool(self.Doc.with_user(user).search([("id", "=", doc.id)]))

    def _todo(self, doc, user):
        return self.env["mail.activity"].search(
            [("res_model", "=", "sarabun.document"), ("res_id", "=", doc.id),
             ("user_id", "=", user.id)]
        )

    def test_take_back_reopens_my_step(self):
        doc, s10, s20 = self._doc()
        att = (
            self.env["ir.attachment"]
            .with_user(self.user_a)
            .create({"name": "a.pdf", "datas": base64.b64encode(b"x")})
        )
        self._act(s10, "complete", self.user_a, sign_comment="<p>ok</p>",
                  sign_attachment_ids=att.ids)
        self.assertEqual(s20.state, "active")
        self.assertTrue(self._can_read(doc, self.user_b))
        self.assertEqual(doc.with_user(self.user_a).my_take_back_step_id, s10)
        self.assertFalse(doc.with_user(self.user_b).my_take_back_step_id)

        s10.with_user(self.user_a).action_take_back("พิมพ์ผิด")

        self.assertEqual(doc.state, "circulating")
        self.assertEqual(s10.state, "active")
        self.assertFalse(s10.acted_by_id or s10.sign_comment or s10.signed_name)
        self.assertFalse(att.exists())
        self.assertTrue(self._todo(doc, self.user_a))
        self.assertEqual(s20.state, "waiting")
        self.assertFalse(self._todo(doc, self.user_b))
        self.assertTrue(self._can_read(doc, self.user_b))  # reached once: a follower
        self.assertIn("พิมพ์ผิด", doc.message_ids[:1].body)
        # act again → the next ลำดับ is reached again
        self._act(s10, "complete", self.user_a)
        self.assertEqual(s20.state, "active")
        self.assertTrue(self._can_read(doc, self.user_b))

    def test_take_back_blocked_once_next_stage_acted(self):
        doc, s10, s20 = self._doc()
        self._act(s10, "complete", self.user_a)
        self._add_step(doc, order=30, verb="acknowledge", user=self.user_a)
        self._act(s20, "complete", self.user_b)
        self.assertFalse(doc.with_user(self.user_a).my_take_back_step_id)
        with self.assertRaises(UserError):
            s10.with_user(self.user_a).action_take_back()

    def test_only_the_actor_takes_back(self):
        doc, s10, _s20 = self._doc()
        self._act(s10, "complete", self.user_a)
        with self.assertRaises(UserError):
            s10.with_user(self.user_b).action_take_back()

    def test_take_back_via_wizard_reason_optional(self):
        doc, s10, _s20 = self._doc()
        self._act(s10, "complete", self.user_a)
        action = doc.with_user(self.user_a).action_open_take_back_wizard()
        wizard = (
            self.env["sarabun.recall.wizard"]
            .with_user(self.user_a)
            .with_context(**action["context"])
            .create({})
        )
        self.assertEqual(wizard.mode, "take_back")
        wizard.action_confirm()
        self.assertEqual(s10.state, "active")
        self.assertEqual(doc.state, "circulating")

    def test_non_gating_take_back_leaves_next_stage(self):
        """Taking back a รับทราบ (non-gating) step reopens only that step."""
        doc = self._make_doc(sender=self.manager)
        s10 = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        ack = self._add_step(doc, order=10, verb="acknowledge", user=self.user_b)
        s20 = self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self._act(ack, "complete", self.user_b)
        self._act(s10, "complete", self.user_a)
        self.assertEqual(s20.state, "active")
        ack.with_user(self.user_b).action_take_back()
        self.assertEqual(ack.state, "active")
        self.assertEqual(s20.state, "active")  # untouched
        self.assertTrue(self._todo(doc, self.user_a))

    def test_gating_take_back_blocked_when_another_gating_passed(self):
        """Two gating holders in one ลำดับ: once one passed it, the other's earlier
        completion can't reopen the ลำดับ."""
        doc = self._make_doc(sender=self.manager)
        a = self._add_step(doc, order=10, verb="endorse", user=self.user_a)
        b = self._add_step(doc, order=10, verb="endorse", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.manager)
        doc.action_send()
        self._act(a, "complete", self.user_a)
        self.assertEqual(b.state, "skipped")
        self.assertTrue(a._can_take_back(self.user_a))
        b.sudo().write({"state": "done", "disposition": "complete"})
        self.assertFalse(a._can_take_back(self.user_a))

    def test_shared_follower_kept(self):
        """A follower added on purpose (sharing) is not unfollowed by a take back —
        only followers the engine added itself."""
        doc, s10, s20 = self._doc()
        doc.message_subscribe(partner_ids=self.user_b.partner_id.ids)  # shared first
        self._act(s10, "complete", self.user_a)
        s10.with_user(self.user_a).action_take_back()
        self.assertIn(self.user_b.partner_id, doc.message_partner_ids)

