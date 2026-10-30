"""Correct the ความเห็น (note) of an acted routing step.

``note`` is readonly and stamped by the engine when the step is acted on; once the
หนังสือ is sent the Route list is read-only, so the correction goes through a row
button and a small wizard (the ADR-0019 pattern). Only a Sarabun Comment Editor may
do it; the write runs ``sudo`` after the authority check because an acted step is
locked to user writes. Every correction is logged to the document chatter.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError

NOTE_EDIT_GROUP = "agx_sarabun_step_note_edit.group_sarabun_step_note_edit"


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    can_edit_note = fields.Boolean(
        compute="_compute_can_edit_note",
        help="True when the current user may correct this acted step's comment — "
        "drives the row button on the Route.",
    )

    def _compute_can_edit_note(self):
        is_editor = self.env.user.has_group(NOTE_EDIT_GROUP)
        for step in self:
            step.can_edit_note = is_editor and bool(step.disposition)

    def _check_note_editable(self):
        self.ensure_one()
        if not self.env.user.has_group(NOTE_EDIT_GROUP):
            raise UserError(_("Only a Sarabun Comment Editor may edit a step comment."))
        if not self.disposition:
            raise UserError(_("Only the comment of an acted step can be edited."))

    def action_open_note_wizard(self):
        self.ensure_one()
        self._check_note_editable()
        return {
            "type": "ir.actions.act_window",
            "name": _("แก้ไขความเห็น"),
            "res_model": "sarabun.step.note.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_step_id": self.id, "default_note": self.note},
        }

    def _set_note(self, note):
        self.ensure_one()
        self._check_note_editable()
        old = self.note or ""
        if (note or "") == old:
            return
        # sudo: an acted step is locked to user writes; authority checked above.
        self.sudo().write({"note": note})
        self.document_id.sudo().message_post(
            body=_("%(user)s แก้ไขความเห็นของ %(step)s: %(old)s → %(new)s")
            % {
                "user": self.env.user.display_name,
                "step": self.name,
                "old": old or "-",
                "new": note or "-",
            }
        )
