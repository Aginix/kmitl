"""Correct the ความเห็น (note) of an acted routing step."""

from odoo.exceptions import UserError
from odoo.tests.common import new_test_user, tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestSarabunStepNoteEdit(SarabunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.editor = new_test_user(
            cls.env,
            login="sb_note_editor",
            name="ผู้แก้ความเห็น",
            # Manager to open any หนังสือ — the comment group grants no access.
            groups="base.group_user,agx_sarabun.group_sarabun_manager,"
            "agx_sarabun_step_note_edit.group_sarabun_step_note_edit",
        )

    def _acted_step(self):
        doc = self._make_doc(sender=self.user_b)
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        with self.mute_pdf():
            doc.action_send()
            self._act(step, "complete", self.user_a, note="ความเห็นเดิม")
        self.assertEqual(step.note, "ความเห็นเดิม")
        return doc, step

    def _apply(self, step, note, user=None):
        user = user or self.editor
        action = step.with_user(user).action_open_note_wizard()
        wizard = (
            self.env["sarabun.step.note.wizard"]
            .with_user(user)
            .with_context(**action["context"])
            .create({"note": note})
        )
        return wizard.action_apply()

    def test_edit_note_after_completion(self):
        doc, step = self._acted_step()
        self.assertEqual(doc.state, "completed")
        acted_by, acted_date = step.acted_by_id, step.acted_date
        self.assertTrue(step.with_user(self.editor).can_edit_note)
        self._apply(step, "ความเห็นใหม่")
        self.assertEqual(step.note, "ความเห็นใหม่")
        # Only the comment changes.
        self.assertEqual(step.acted_by_id, acted_by)
        self.assertEqual(step.acted_date, acted_date)
        self.assertIn("ความเห็นใหม่", doc.message_ids[0].body)

    def test_requires_comment_editor(self):
        _doc, step = self._acted_step()
        self.assertFalse(step.with_user(self.manager).can_edit_note)
        with self.assertRaises(UserError):
            step.with_user(self.manager).action_open_note_wizard()

    def test_unacted_step_not_editable(self):
        doc = self._make_doc(sender=self.user_b)
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        self.assertFalse(step.with_user(self.editor).can_edit_note)
        with self.assertRaises(UserError):
            step.with_user(self.editor).action_open_note_wizard()
