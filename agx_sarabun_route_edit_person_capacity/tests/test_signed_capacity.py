"""Correct a signed บุคลากร step's ตำแหน่ง (ADR-0019)."""

from odoo.exceptions import UserError
from odoo.tests.common import new_test_user, tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestSarabunSignedCapacity(SarabunCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.editor = new_test_user(
            cls.env,
            login="sb_capacity_editor",
            name="ผู้แก้ตำแหน่ง",
            groups="base.group_user,agx_sarabun_route_edit.group_sarabun_route_edit",
        )
        # emp_a holds both pos and pos_multi (SarabunCommon); a Position they don't.
        cls.pos_other = cls.Position.create(
            {"name": "ตำแหน่งอื่น", "holder_ids": [(6, 0, cls.emp_b.ids)]}
        )

    def _signed_step(self, complete_doc=True):
        """Sender user_b; a บุคลากร step on user_a signed in capacity ``pos``. With
        ``complete_doc`` False a later step keeps the หนังสือ circulating."""
        doc = self._make_doc(sender=self.user_b)
        step = self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        step.position_id = self.pos
        if not complete_doc:
            self._add_step(doc, order=20, verb="endorse", user=self.user_b)
        with self.mute_pdf():
            doc.action_send()
            self._act(step, "complete", self.user_a, signed_as_position_id=self.pos.id)
        self.assertEqual(step.signed_position_name, self.pos.name)
        return doc, step

    def _apply(self, step, position, user=None):
        action = step.with_user(
            user or self.editor
        ).action_open_signed_capacity_wizard()
        wizard = (
            self.env["sarabun.signed.capacity.wizard"]
            .with_user(user or self.editor)
            .with_context(**action["context"])
            .create({"position_id": position.id})
        )
        return wizard.action_apply()

    def test_correct_capacity_after_completion(self):
        doc, step = self._signed_step()
        self.assertEqual(doc.state, "completed")
        signed_name, signed_date = step.signed_name, step.acted_date
        self.assertTrue(step.with_user(self.editor).can_edit_signed_capacity)
        self._apply(step, self.pos_multi)
        self.assertEqual(step.position_id, self.pos_multi)
        self.assertEqual(step.signed_as_position_id, self.pos_multi)
        self.assertEqual(step.signed_position_name, self.pos_multi.name)
        # Only the capacity changes.
        self.assertEqual(step.signed_name, signed_name)
        self.assertEqual(step.acted_date, signed_date)

    def test_correct_capacity_while_circulating(self):
        doc, step = self._signed_step(complete_doc=False)
        self.assertEqual(doc.state, "circulating")
        self._apply(step, self.pos_multi)
        self.assertEqual(step.signed_position_name, self.pos_multi.name)

    def test_position_not_held_raises(self):
        _doc, step = self._signed_step()
        with self.assertRaises(UserError):
            self._apply(step, self.pos_other)

    def test_requires_route_editor(self):
        _doc, step = self._signed_step()
        self.assertFalse(step.with_user(self.manager).can_edit_signed_capacity)
        with self.assertRaises(UserError):
            step.with_user(self.manager).action_open_signed_capacity_wizard()

    def test_not_for_position_mode_step(self):
        doc = self._make_doc(sender=self.user_b)
        step = self._add_step(
            doc,
            order=10,
            verb="sign_approve",
            target_mode="position",
            position=self.pos,
        )
        with self.mute_pdf():
            doc.action_send()
            self._act(step, "complete", self.user_a)
        self.assertFalse(step.with_user(self.editor).can_edit_signed_capacity)
        with self.assertRaises(UserError):
            step.with_user(self.editor).action_open_signed_capacity_wizard()

    def test_route_edit_rechecks_capacity(self):
        """Re-targeting a waiting บุคลากร step to someone who does not hold its
        capacity is refused at save, not when they come to sign."""
        doc = self._make_doc(sender=self.user_b)
        self._add_step(doc, order=10, verb="endorse", user=self.user_b)
        waiting = self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        waiting.position_id = self.pos
        doc.action_send()
        with self.assertRaises(UserError):
            doc.with_user(self.editor).write(
                {"routing_step_ids": [(1, waiting.id, {"employee_id": self.emp_b.id})]}
            )

    def test_no_chatter_message(self):
        doc, step = self._signed_step()
        count = len(doc.message_ids)
        self._apply(step, self.pos_multi)
        self.assertEqual(len(doc.message_ids), count)
