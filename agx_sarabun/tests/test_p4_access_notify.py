# -*- coding: utf-8 -*-
"""P4 — access record-rules + mail.activity notifications."""
from odoo.tests.common import tagged

from odoo.addons.agx_sarabun.tests.common import SarabunCommon


@tagged("post_install", "-at_install")
class TestP4Access(SarabunCommon):
    def _can_read(self, doc, user):
        return bool(self.Doc.with_user(user).search([("id", "=", doc.id)]))

    def test_sender_can_read(self):
        """The author sees their own หนังสือ."""
        doc = self._make_doc(sender=self.user_a)
        self.assertTrue(self._can_read(doc, self.user_a))

    def test_non_actor_cannot_read(self):
        """A user with no relation to the document cannot see it."""
        doc = self._make_doc(sender=self.user_a)
        self.assertFalse(self._can_read(doc, self.user_b))

    def test_waiting_step_grants_no_visibility(self):
        """A pre-seeded but still-waiting step grants NO read."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        # not sent yet → step is waiting
        self.assertFalse(self._can_read(doc, self.user_b))

    def test_active_step_actor_can_read(self):
        """An actor of an active step can read — keyed off the snapshot holders."""
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_b)
        doc.action_send()
        self.assertTrue(self._can_read(doc, self.user_b))

    def test_position_actor_no_personal_target_can_read(self):
        """Position-targeted actor (holder) can read once active — the old hide bug fix.

        Visibility keys off actor_user_ids (snapshot), not a recipient.user_id, so a
        Position/Unit target resolves to readable users.
        """
        doc = self._make_doc(sender=self.user_a)
        self._add_step(doc, order=10, verb="sign_approve", target_mode="position",
                       position=self.pos)  # holder = user_a
        doc.action_send()
        self.assertTrue(self._can_read(doc, self.user_a))

    def test_manager_sees_all(self):
        """Managers retain see-all in v1."""
        doc = self._make_doc(sender=self.user_a)
        self.assertTrue(self._can_read(doc, self.manager))

    # ----------------------------------------------------------- notifications
    def _activities(self, doc, user):
        return self.env["mail.activity"].search([
            ("res_model", "=", "sarabun.document"),
            ("res_id", "=", doc.id),
            ("user_id", "=", user.id),
        ])

    def test_activity_per_holder_and_first_to_act_autoclear(self):
        """Each holder of an active gating step gets an activity; first-to-act clears the rest."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", target_mode="position",
                       position=self.pos_multi)  # holders a + b
        self._add_step(doc, order=20, verb="sign_approve", user=self.user_a)
        doc.action_send()
        self.assertTrue(self._activities(doc, self.user_a))
        self.assertTrue(self._activities(doc, self.user_b))

        step10 = doc.routing_step_ids.filtered(lambda s: s.order == 10)
        self._act(step10, "complete", self.user_a)  # first-to-act
        # the other holder's pending activity is auto-cleared
        self.assertFalse(self._activities(doc, self.user_b))

    def test_acknowledge_step_schedules_no_activity(self):
        """รับทราบ / non-gating steps never raise an activity (inbox-tray only)."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)  # gating
        self._add_step(doc, order=10, verb="acknowledge", target_mode="person",
                       user=self.user_b)  # non-gating
        doc.action_send()
        self.assertTrue(self._activities(doc, self.user_a))      # gating → activity
        self.assertFalse(self._activities(doc, self.user_b))     # acknowledge → none

    # ------------------------------------------------------------- inbox tray
    def test_inbox_lists_my_active_step_documents(self):
        """get_my_sarabun_inbox (systray tray) returns docs where I have an active step."""
        doc = self._make_doc()
        self._add_step(doc, order=10, verb="sign_approve", user=self.user_a)
        doc.action_send()
        inbox_a = self.Doc.with_user(self.user_a).get_my_sarabun_inbox()
        self.assertEqual(inbox_a["total_count"], 1)
        self.assertEqual(inbox_a["documents"][0]["id"], doc.id)
        # a user with no active step has an empty inbox
        inbox_b = self.Doc.with_user(self.user_b).get_my_sarabun_inbox()
        self.assertEqual(inbox_b["total_count"], 0)
