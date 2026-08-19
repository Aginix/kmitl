from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _todo_sound_enabled_for(self, partner):
        """Per-source refinement (ADR-0014): a notification about e-Saraban work
        obeys the dedicated sarabun toggle, everything else the general one — so a
        user drowning in general Todos can silence those yet still be pinged for a
        หนังสือ. Routed by ``res_model`` (``sarabun.document`` vs the rest).

        This method is only ever reached when ``mail_activity_todo_sound`` is
        installed (it owns the caller ``_todo_payload``); that add-on defines both
        the base method — resolved via ``super()`` — and the general toggle. The
        agx_sarabun_todo bridge loads after it (deeper in the dependency graph), so
        this override wins in the MRO.
        """
        only_sarabun = bool(self) and all(
            m == "sarabun.document" for m in self.mapped("res_model")
        )
        if only_sarabun:
            user = partner.user_ids[:1].sudo()
            return bool(user) and user.todo_sound_sarabun_enabled
        return super()._todo_sound_enabled_for(partner)
