"""Standard-comment picker on the Act-on-step wizard."""

from markupsafe import Markup

from odoo import api, fields, models


class SarabunStepActWizard(models.TransientModel):
    _inherit = "sarabun.step.act.wizard"

    standard_comment_id = fields.Many2one(
        "sarabun.standard.comment",
        string="ข้อความมาตรฐาน (Standard comment)",
        help="Pick a canned เกษียน text — it replaces the comment below. "
        "The comment stays freely editable afterwards.",
    )

    @api.onchange("standard_comment_id")
    def _onchange_standard_comment_id(self):
        # Guarded on purpose: on a new record Odoo 16 fires EVERY onchange method
        # (the initial call has an empty field_name), so an unconditional write
        # here would wipe the verb-default prefill set by _onchange_step_id.
        if self.standard_comment_id:
            self.note = self._wrap_body(self.standard_comment_id.body)

    @api.onchange("step_id")
    def _onchange_step_id(self):
        res = super()._onchange_step_id()
        default_comment = self.step_id.verb.default_standard_comment_id
        if default_comment:
            self.standard_comment_id = default_comment
            self.note = self._wrap_body(default_comment.body)
        return res

    @api.model
    def _wrap_body(self, text):
        """Wrap plain text body in <p> for the Html note field."""
        if not text:
            return False
        return Markup("<p>%s</p>") % text
