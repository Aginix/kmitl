# -*- coding: utf-8 -*-
"""mail_activity_todo_sound — server-side sound decision (ADR-0014).

The bus payload alone (``{refresh: True}``) can't distinguish new work from a
clear, so the sound intent is carried on ``_todo_notify(sound=…)`` (create → True;
write/unlink → False) and turned into ``payload.sound`` per-recipient by
``_todo_payload`` under a per-user preference. The client simply obeys the flag.
"""
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestTodoSound(TransactionCase):
    def _make_activity(self, user):
        partner = self.env["res.partner"].create({"name": "Anchor"})
        act = partner.activity_schedule(
            "mail.mail_activity_data_todo", user_id=user.id
        )
        return act

    def test_sound_payload_when_enabled(self):
        user = new_test_user(self.env, login="snd_on", groups="base.group_user")
        user.todo_sound_enabled = True
        act = self._make_activity(user)
        self.assertTrue(act._todo_payload(user.partner_id, True).get("sound"))

    def test_no_sound_when_disabled(self):
        user = new_test_user(self.env, login="snd_off", groups="base.group_user")
        user.todo_sound_enabled = False
        act = self._make_activity(user)
        self.assertNotIn("sound", act._todo_payload(user.partner_id, True))

    def test_no_sound_on_silent_transition(self):
        """sound=False (a write/unlink transition) never plays, even with the pref on."""
        user = new_test_user(self.env, login="snd_silent", groups="base.group_user")
        user.todo_sound_enabled = True
        act = self._make_activity(user)
        self.assertNotIn("sound", act._todo_payload(user.partner_id, False))

    def test_self_writeable_preference(self):
        """A user may toggle their own sound preference (SELF_WRITEABLE)."""
        user = new_test_user(self.env, login="snd_self", groups="base.group_user")
        user.with_user(user).write({"todo_sound_enabled": False})
        self.assertFalse(user.todo_sound_enabled)
