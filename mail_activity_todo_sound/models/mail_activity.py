from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _todo_payload(self, partner, sound):
        """Turn the create-time ``sound`` intent (ADR-0014) into an audible ding
        when the recipient has the preference on. Silent otherwise, and silent on
        write/unlink (which never pass ``sound=True``). The client handler simply
        obeys ``payload.sound``."""
        payload = super()._todo_payload(partner, sound)
        if sound and self._todo_sound_enabled_for(partner):
            payload["sound"] = True
        return payload

    def _todo_sound_enabled_for(self, partner):
        """Whether ``partner`` wants a sound for this notification. Base decision is
        the single per-user toggle; the agx_sarabun_todo bridge overrides this to
        route by source model (sarabun vs general — ADR-0014)."""
        user = partner.user_ids[:1].sudo()
        return bool(user) and user.todo_sound_enabled
