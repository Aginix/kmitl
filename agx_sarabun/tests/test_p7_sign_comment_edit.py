"""P7 — ความเห็นในการลงนาม (Html + files), แก้ไขเอกสารได้, act buttons."""

import base64

from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP7SignCommentEdit(SarabunCommon):
    def _attachment(self, user, name="ประกอบ.pdf"):
        return (
            self.env["ir.attachment"]
            .with_user(user)
            .create({"name": name, "datas": base64.b64encode(b"%PDF-1.4 x")})
        )

    # ------------------------------------------------------------ sign comment
    def test_sign_comment_and_files_stamped_on_step(self):
        """The wizard stores the Html comment + files on the step, which owns the
        files: readable with the หนังสือ, locked against write/unlink."""
        self._verb("endorse").allow_sign_comment = True
        doc = self._make_doc(sender=self.user_a)
        step = self._add_step(doc, order=10, verb="endorse", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        att = self._attachment(self.user_b)
        wizard = (
            self.env["sarabun.step.act.wizard"]
            .with_user(self.user_b)
            .create(
                {
                    "step_id": step.id,
                    "sign_comment": "<p>เห็นควร<b>อนุมัติ</b></p>",
                    "sign_attachment_ids": [(6, 0, att.ids)],
                }
            )
        )
        wizard.action_confirm()
        self.assertEqual(step.state, "done")
        self.assertIn("อนุมัติ", step.sign_comment)
        self.assertEqual(step.sign_attachment_ids, att)
        self.assertEqual((att.res_model, att.res_id), ("sarabun.routing.step", step.id))
        # readers of the หนังสือ download it; nobody but the engine may delete it
        self.assertTrue(att.with_user(self.user_a).datas)
        with self.assertRaises(AccessError):
            att.with_user(self.user_a).unlink()
        self.assertEqual(doc.sign_attachment_ids, att)

    def test_return_drops_old_round_sign_files(self):
        """ตีกลับ deletes the old round with its sign comment files (ADR-0023)."""
        self._verb("endorse").allow_sign_comment = True
        doc = self._make_doc(sender=self.user_a)
        s10 = self._add_step(doc, order=10, verb="endorse", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.manager)
        doc.action_send()
        att = self._attachment(self.user_b)
        self._act(s10, "complete", self.user_b, sign_attachment_ids=att.ids)
        self.assertEqual(doc.sign_attachment_ids, att)
        wizard = (
            self.env["sarabun.step.act.wizard"]
            .with_user(self.manager)
            .with_context(sarabun_disposition="return")
            .create({"step_id": self._active_step(doc).id, "note": "แก้"})
        )
        wizard.action_confirm()
        self.assertEqual(doc.state, "returned")
        self.assertFalse(att.exists())
        self.assertFalse(doc.sign_attachment_ids)

    def test_returner_sent_to_inbox(self):
        """A returner reached only in the deleted round can't reload the หนังสือ —
        the wizard opens their incoming box instead of closing."""
        doc = self._make_doc(sender=self.user_a)
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        action = (
            self.env["sarabun.step.act.wizard"]
            .with_user(self.user_b)
            .with_context(sarabun_disposition="return")
            .create({"step_id": step.id, "note": "แก้"})
            .action_confirm()
        )
        self.assertEqual(doc.state, "returned")
        self.assertFalse(self.Doc.with_user(self.user_b).search([("id", "=", doc.id)]))
        self.assertEqual(action.get("res_model"), "sarabun.document")
        self.assertEqual(action.get("type"), "ir.actions.act_window")

    def test_sign_comment_ignored_when_verb_disallows(self):
        self._verb("endorse").allow_sign_comment = False
        doc = self._make_doc(sender=self.user_a)
        step = self._add_step(doc, order=10, verb="endorse", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self._act(step, "complete", self.user_b, sign_comment="<p>x</p>")
        self.assertFalse(step.sign_comment)

    # --------------------------------------------------------- content editor
    def _editor_doc(self):
        self._verb("verify").can_edit_document = True
        doc = self._make_doc(sender=self.user_a)
        step = self._add_step(doc, order=10, verb="verify", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        return doc, step

    def test_editor_can_edit_content_while_step_active(self):
        doc, step = self._editor_doc()
        as_b = doc.with_user(self.user_b)
        self.assertTrue(as_b.can_edit_content)
        as_b.write({"subject": "เรื่องใหม่", "content": "<p>แก้</p>"})
        self.assertEqual(doc.subject, "เรื่องใหม่")
        self.assertIn("แก้ไขเอกสารระหว่างเวียน", doc.message_ids[:1].body)
        # outside the whitelist
        with self.assertRaises(AccessError):
            as_b.write({"sender_suffix": "x"})
        # the right ends once the step is acted on
        self._act(step, "complete", self.user_b)
        self.assertFalse(doc.with_user(self.user_b).can_edit_content)
        with self.assertRaises(AccessError):
            doc.with_user(self.user_b).write({"subject": "อีกครั้ง"})

    def test_non_editor_verb_stays_read_only(self):
        self._verb("verify").can_edit_document = False
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="verify", user=self.user_b)
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        with self.assertRaises(AccessError):
            doc.with_user(self.user_b).write({"subject": "x"})

    def test_editor_can_upload_enclosure(self):
        doc, _step = self._editor_doc()
        att = (
            self.env["ir.attachment"]
            .with_user(self.user_b)
            .create(
                {
                    "name": "แนบ.pdf",
                    "datas": base64.b64encode(b"%PDF-1.4 x"),
                    "res_model": "sarabun.document",
                    "res_id": doc.id,
                }
            )
        )
        doc.with_user(self.user_b).write({"enclosure_attachment_ids": [(4, att.id)]})
        self.assertIn(att, doc.enclosure_attachment_ids)

    def test_editor_cannot_publish_foreign_attachment(self):
        """Linking a file the editor cannot read (another record's, or another
        user's unsaved upload) as an enclosure is refused, not copied over."""
        doc, _step = self._editor_doc()
        private = self._make_doc(subject="ร่างส่วนตัว", sender=self.user_a)
        foreign = self.env["ir.attachment"].create(
            {
                "name": "ลับ.pdf",
                "datas": base64.b64encode(b"x"),
                "res_model": "sarabun.document",
                "res_id": private.id,
            }
        )
        orphan = self._attachment(self.user_a, "ของคนอื่น.pdf")
        for att in (foreign, orphan):
            with self.assertRaises(AccessError):
                doc.with_user(self.user_b).write(
                    {"enclosure_attachment_ids": [(4, att.id)]}
                )
        self.assertFalse(doc.enclosure_attachment_ids)

    # ----------------------------------------------------------------- buttons
    def test_button_label_and_return_flag(self):
        verb = self._verb("sign_approve")
        verb.button_emoji = False
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        as_b = doc.with_user(self.user_b)
        self.assertEqual(as_b.my_step_button_label, "✍️ %s" % verb.name)
        self.assertTrue(as_b.my_step_can_return)
        action = as_b.with_context(sarabun_disposition="return").action_act_on_my_step()
        wizard = (
            self.env["sarabun.step.act.wizard"]
            .with_user(self.user_b)
            .with_context(**action["context"])
            .create({})
        )
        self.assertEqual(wizard.disposition, "return")

    def test_wizard_offers_no_reject(self):
        values = dict(
            self.env["sarabun.step.act.wizard"]._fields["disposition"].selection
        )
        self.assertNotIn("reject", values)
