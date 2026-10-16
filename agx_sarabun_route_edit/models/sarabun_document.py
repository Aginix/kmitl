"""Admin route edit (ADR-0018) — fix the Route of a หนังสือ while it circulates.

An admin in ``group_sarabun_route_edit`` edits the live steps directly in the Route
list (the guards live on ``sarabun.routing.step``). This side owns the document-level
pieces: unlocking the list, validating the Route once the batch of edits is saved,
advancing the engine, and the per-document "re-resolve holders" button used after a
Position's holder changes. No agx_sarabun core edit beyond these ``_inherit`` hooks.
"""

from itertools import takewhile

from odoo import _, api, fields, models
from odoo.exceptions import UserError

ROUTE_EDIT_GROUP = "agx_sarabun_route_edit.group_sarabun_route_edit"


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    can_edit_route = fields.Boolean(
        compute="_compute_can_edit_route",
        string="Can Edit Route",
        help="True when the หนังสือ is circulating and the current user may edit its "
        "Route (member of group_sarabun_route_edit) — unlocks the Route list.",
    )

    @api.depends("state")
    def _compute_can_edit_route(self):
        is_editor = self.env.user.has_group(ROUTE_EDIT_GROUP)
        for record in self:
            record.can_edit_route = is_editor and record.state == "circulating"

    # ------------------------------------------------------------------ guards
    def _is_route_edit(self):
        """True when a step change on this หนังสือ is a USER edit of a circulating
        Route. Engine writes run sudo (act_on_step, ตีกลับ, Reset, and the sender's
        ดึงกลับ via ``_recreate_chain_verbatim`` below), so they pass."""
        self.ensure_one()
        return not self.env.su and self.state == "circulating"

    def _check_route_edit_access(self):
        if not self.env.user.has_group(ROUTE_EDIT_GROUP):
            raise UserError(
                _(
                    "The Route of a circulating document can only be edited by a "
                    "Sarabun Route Editor."
                )
            )

    def _check_route_edit_order(self, order):
        """A step may only be placed after the last Stage already passed — a passed
        Stage is history (the current Stage, or a new one before the next, is fine)."""
        self.ensure_one()
        orders = sorted(set(self.routing_step_ids.mapped("order")))
        passed = list(takewhile(self._stage_complete, orders))
        if passed and order <= passed[-1]:
            raise UserError(
                _(
                    "ลำดับ %(order)s has already passed — a step may only be placed "
                    "after ลำดับ %(passed)s."
                )
                % {"order": order, "passed": passed[-1]}
            )

    def _check_route_edit_route(self):
        """The edited Route must still pass what ``action_send`` checks."""
        self.ensure_one()
        live = self.routing_step_ids.filtered(lambda s: s.state != "skipped")
        if not live.filtered("gating"):
            raise UserError(
                _(
                    "The Route must keep at least one gating step (เห็นชอบ or ลงนาม-อนุมัติ)."
                )
            )
        if not self.register_number_id and not live.filtered("verb.issues_number"):
            raise UserError(_("เส้นทางต้องมีขั้นตอนที่ออกเลขที่หนังสือ (เช่น ลงนามในใบปะหน้า)"))

    def _finalize_route_edit(self):
        """Validate the edited Route, then let the engine react: activate a step
        added to the current Stage, or advance when the last pending gating step of
        the Stage was removed. Inside a form save (one batch of o2m commands) this
        waits for the document write to run it once, after every command."""
        if self.env.context.get("sarabun_route_edit_batch"):
            return
        for doc in self:
            doc._check_route_edit_route()
            doc.sudo()._advance_stage()
            # A step the edit activated must have somebody who can act on it.
            doc.routing_step_ids.filtered(
                lambda s: s.state == "active"
            )._check_route_edit_actors()

    # ------------------------------------------------------------------ ORM
    def write(self, vals):
        """Saving the form sends the Route edits as one batch of o2m commands —
        validate and advance once, after all of them are applied."""
        edited = self.browse()
        if "routing_step_ids" in vals:
            edited = self.filtered(lambda d: d._is_route_edit())
        if not edited:
            return super().write(vals)
        res = super(
            SarabunDocument, self.with_context(sarabun_route_edit_batch=True)
        ).write(vals)
        edited._finalize_route_edit()
        return res

    def _route_edit_revoke(self, recipients):
        """Take these recipient rows off the Route: the read they keyed goes with
        them (ADR-0013). Anyone the หนังสือ no longer reaches is also unfollowed (their
        to-do subscribed them), so chatter stops notifying them. The sender stays."""
        self.ensure_one()
        users = recipients.user_id
        recipients.sudo().unlink()
        gone = users - self.reached_user_ids - self.sender_user_id
        if gone:
            self.sudo().message_unsubscribe(partner_ids=gone.partner_id.ids)

    # ------------------------------------------------------------------ engine
    def _recreate_chain_verbatim(self):
        # The sender's ดึงกลับ recreates the Route in their env while still
        # circulating — an engine write, not a route edit.
        return super(SarabunDocument, self.sudo())._recreate_chain_verbatim()

    # ------------------------------------------------------------------ actions
    def action_refresh_route_holders(self):
        """ดึงผู้ดำรงตำแหน่งปัจจุบัน — re-resolve the active Position / unit-clerk steps
        to their CURRENT holders (after e.g. a new คณบดี is set on the Position):
        the old holders' to-dos are cleared, they lose access, and the new holders
        get the to-dos. Waiting steps need nothing — they resolve when they
        activate."""
        self.ensure_one()
        self._check_route_edit_access()
        if self.state != "circulating":
            raise UserError(_("Only a circulating document's Route can be refreshed."))
        steps = self.routing_step_ids.filtered(
            lambda s: (
                s.state == "active"
                and not s.is_originator
                and s.target_mode in ("position", "unit")
            )
        )
        changes = [
            _("%(step)s: %(old)s → %(new)s")
            % {
                "step": step.name,
                "old": ", ".join(former.mapped("name")) or "-",
                "new": ", ".join(step.actor_user_ids.mapped("name")),
            }
            for step, former in steps._route_edit_reresolve().items()
        ]
        if changes:
            self.message_post(
                body=_("Route holders refreshed by %(user)s: %(changes)s")
                % {
                    "user": self.env.user.display_name,
                    "changes": "; ".join(changes),
                }
            )
        # Run from the Action menu: a server action must return an action dict, and
        # closing through ``next`` makes the form reload the re-resolved Route.
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if changes else "info",
                "message": _("Route holders refreshed.")
                if changes
                else _("The active steps already go to the current holders."),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
