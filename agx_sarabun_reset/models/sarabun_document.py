# -*- coding: utf-8 -*-
"""Admin reset-to-draft (ADR-0011) — the one override ดึงกลับ cannot serve.

Returns a หนังสือ from ANY non-draft state (incl. the otherwise-terminal
``rejected`` / ``cancelled``, and a signed ``completed``) to an editable
``draft``, keeping its registered number and its ORIGINAL Route so a mistake
found after signing can be corrected and re-sent from the start.

It is a deliberate, dangerous override: it bypasses ``_check_sender_withdraw_allowed``
(the guard it exists to override), un-freezes an official signed record, and pulls a
document out of a terminal state. Hence a separate, optional module gated on its own
``group_sarabun_reset``. No agx_sarabun core edit beyond this ``_inherit`` extension.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    can_reset = fields.Boolean(
        compute="_compute_can_reset",
        string="Can Reset",
        help="True when the หนังสือ is not a draft and the current user may reset it "
        "(member of group_sarabun_reset) — drives the Reset button visibility.",
    )

    @api.depends("state")
    def _compute_can_reset(self):
        is_reset = self.env.user.has_group("agx_sarabun_reset.group_sarabun_reset")
        for record in self:
            record.can_reset = is_reset and record.state != "draft"

    def action_open_reset_wizard(self):
        """Open the reset wizard (collects the mandatory reason)."""
        self.ensure_one()
        if self.state == "draft":
            raise UserError(_("This document is already a draft."))
        return {
            "type": "ir.actions.act_window",
            "name": _("รีเซ็ต (Reset to Draft)"),
            "res_model": "sarabun.reset.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_document_id": self.id},
        }

    def action_reset_to_draft(self, reason):
        """Force a non-draft หนังสือ back to editable draft (ADR-0011), keeping its
        number and recreating its ORIGINAL seed Route. Bypasses the sender-withdraw
        guard on purpose — this IS the override for the signed / completed / terminal
        cases ดึงกลับ refuses."""
        self.ensure_one()
        # --- Guard (as the acting user) ---
        if self.state == "draft":
            raise UserError(_("This document is already a draft."))
        if not self.env.user.has_group("agx_sarabun_reset.group_sarabun_reset"):
            raise UserError(_("You are not allowed to reset documents."))
        if not reason:
            raise UserError(_("A reason is required to reset the document."))

        prev_state = self.state
        # The mutation is a SYSTEM override (it un-freezes a signed record and may pull
        # the doc out of a terminal state the acting user cannot write); authority is
        # checked above, so run it privileged — like the other lifecycle transitions.
        doc = self.sudo()
        # Clear the live steps' to-dos before they are archived.
        doc.routing_step_ids._clear_activities()
        # Archive the finished attempt, recreate the ORIGINAL seed Route (drop runtime
        # เกษียนสั่งการ insertions).
        doc._reset_restart_chain()
        # Keep the number; reclaim it if resetting out of rejected / cancelled (voided).
        if (
            prev_state in ("rejected", "cancelled")
            and doc.register_number_id.state == "voided"
        ):
            doc._reclaim_voided_number(reason)
        # Un-freeze the ฉบับลงนาม — discard the prior PDF (writing False on an
        # attachment field removes the attachment; audit survives on the archived steps).
        doc.write({
            "signed_pdf": False,
            "signed_pdf_filename": False,
            "signed_at": False,
        })
        doc.state = "draft"
        # From the origin's view Reset IS a ดึงกลับ — roll it back the same way.
        doc._call_origin("_on_sarabun_recalled", doc)
        doc.message_post(body=_(
            "Document reset to draft by %(user)s. Reason: %(reason)s"
        ) % {"user": self.env.user.display_name, "reason": reason})
        return True

    def _reset_restart_chain(self):
        """Archive the finished attempt and recreate the ORIGINAL seed Route as fresh
        waiting steps — ``_restart_chain`` with its no-template fallback narrowed from
        "recreate all live steps" to the seed backbone only (created_by_disposition
        == 'seed'), so runtime เกษียนสั่งการ ('direct') insertions are dropped."""
        self.ensure_one()
        seeds = [
            s._resume_seed_vals()
            for s in self.routing_step_ids.filtered(
                lambda s: s.created_by_disposition == "seed"
            ).sorted("order")
        ]
        self._bump_attempt_and_archive()
        self._seed_route_from_template()
        if not self.routing_step_ids:
            new_seq = self.attempt_seq or 1
            self.routing_step_ids = [
                (0, 0, dict(v, attempt_seq=new_seq)) for v in seeds
            ]
        # Re-add the mandatory originator row unless the recreated seeds already carry one.
        self._ensure_originator_step()

    def _reclaim_voided_number(self, reason):
        """Un-void this document's OWN register number (voided → used) on reset out of
        rejected / cancelled (ADR-0011 / *Voided number*). Never recycles to another
        document; the reclaim is audited on the ledger row + chatter."""
        self.ensure_one()
        number = self.register_number_id
        prior_note = (number.note + "\n") if number.note else ""
        number.write({
            "state": "used",
            "void_reason": False,
            "void_date": False,
            "note": prior_note + _("Reclaimed on reset. Reason: %s") % reason,
        })
