# -*- coding: utf-8 -*-
"""agx_sarabun_todo — the e-Saraban → unified Todo inbox bridge (ADR-0014).

Reuses agx_sarabun's SarabunCommon fixtures. Asserts the two native activity types
are tagged with the right todo_category, that a sent หนังสือ raises Todos of the
correct category per holder, that the unified count sees each หนังสือ exactly once
(one bell, no double count), and that a read-only involved holder opens their
รับทราบ Todo with no AccessError (relies on _mail_post_access='read', ADR-0013).
"""
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestSarabunTodoBridge(SarabunCommon):
    def _activities(self, doc, user):
        return self.env["mail.activity"].search([
            ("res_model", "=", "sarabun.document"),
            ("res_id", "=", doc.id),
            ("user_id", "=", user.id),
        ])

    def test_activity_types_tagged(self):
        """The bridge tags the two core types with todo_category."""
        action_type = self.env.ref("agx_sarabun.mail_activity_sarabun_action")
        ack_type = self.env.ref("agx_sarabun.mail_activity_sarabun_ack")
        self.assertEqual(action_type.todo_category, "execution")
        self.assertEqual(ack_type.todo_category, "acknowledgement")

    def test_scheduled_todos_carry_category(self):
        """A gating holder's Todo is Execution; a รับทราบ holder's is Acknowledgement
        (the category flows from the type onto the activity via mail_activity_todo)."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)  # gating
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.manager)  # non-gating รับทราบ
        doc.with_user(self.user_a).action_send()
        exec_act = self._activities(doc, self.user_b)
        ack_act = self._activities(doc, self.manager)
        self.assertEqual(exec_act.todo_category, "execution")
        self.assertEqual(ack_act.todo_category, "acknowledgement")

    def test_single_count_no_double(self):
        """The unified inbox counts the หนังสือ once for the holder (one bell) — the
        parallel sarabun tray/count is gone (ADR-0014)."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.with_user(self.user_a).action_send()
        payload = self.env["res.users"].with_user(self.user_b).get_my_todo_count()
        sarabun_groups = [
            g for g in payload["groups"] if g["model"] == "sarabun.document"
        ]
        self.assertEqual(len(sarabun_groups), 1)
        self.assertEqual(sarabun_groups[0]["total_count"], 1)

    def test_readonly_holder_opens_ack_todo_no_accesserror(self):
        """A read-only involved holder (not the sender) opens their รับทราบ Todo with
        no AccessError — mail.activity read delegates to the doc's _mail_post_access,
        set to 'read' (ADR-0013)."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)  # gating
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.user_b)  # read-only รับทราบ holder
        doc.with_user(self.user_a).action_send()
        # user_b is read-only on the doc, yet reads AND opens (reads fields of) their
        # own activity without tripping the mail.activity access gate.
        act = self._activities(doc, self.user_b)
        self.assertTrue(act)
        as_b = act.with_user(self.user_b)
        self.assertTrue(as_b.exists())
        as_b.read(["summary", "res_id", "activity_type_id"])  # must not raise
