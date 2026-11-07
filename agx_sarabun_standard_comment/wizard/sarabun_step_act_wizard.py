# -*- coding: utf-8 -*-
"""Standard-comment picker on the Act-on-step wizard."""
from odoo import api, fields, models
from odoo.tools import plaintext2html


class SarabunStepActWizard(models.TransientModel):
    _inherit = "sarabun.step.act.wizard"

    standard_comment_id = fields.Many2one(
        "sarabun.standard.comment",
        string="ข้อความมาตรฐาน (Standard comment)",
        help="Pick a canned เกษียน text — it replaces the comment below. "
        "The comment stays freely editable afterwards.",
    )

    def _set_standard_comment(self, body):
        # Fill the box on screen: ความเห็นในการลงนาม (Html) when signing, else the
        # plain-text เหตุผล.
        if self.disposition == "complete" and self.step_allow_sign_comment:
            self.sign_comment = plaintext2html(body or "")
        else:
            self.note = body

    @api.onchange("standard_comment_id")
    def _onchange_standard_comment_id(self):
        # Guarded on purpose: on a new record Odoo 16 fires EVERY onchange method
        # (the initial call has an empty field_name), so an unconditional write
        # here would wipe the verb-default prefill set by _onchange_step_id.
        if self.standard_comment_id:
            self._set_standard_comment(self.standard_comment_id.body)

    @api.onchange("step_id")
    def _onchange_step_id(self):
        res = super()._onchange_step_id()
        default_comment = self.step_id.verb.default_standard_comment_id
        if (
            default_comment
            and self.disposition == "complete"
            and self.step_allow_sign_comment
        ):
            self.standard_comment_id = default_comment
            self._set_standard_comment(default_comment.body)
        return res
