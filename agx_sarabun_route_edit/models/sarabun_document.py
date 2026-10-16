"""Admin route edit (ADR-0018) — fix the Route of a หนังสือ while it circulates.

An admin in ``group_sarabun_route_edit`` edits the live steps directly in the Route
list (the guards live on ``sarabun.routing.step``). This side owns the document-level
pieces: unlocking the list, validating the Route once the batch of edits is saved,
advancing the engine, and the per-document "re-resolve holders" button used after a
Position's holder changes. No agx_sarabun core edit beyond these ``_inherit`` hooks.
"""

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
        Route. Engine writes run sudo (act_on_step, ตีกลับ, Reset) or carry the
        ``sarabun_route_engine`` context (the sender's ดึงกลับ), so they pass."""
        self.ensure_one()
        return (
            not self.env.su
            and not self.env.context.get("sarabun_route_engine")
            and self.state == "circulating"
        )

    def _check_route_edit_access(self):
        if not self.env.user.has_group(ROUTE_EDIT_GROUP):
            raise UserError(
                _(
                    "The Route of a circulating document can only be edited by a "
                    "Sarabun Route Editor."
                )
            )

    def _route_edit_frontier(self):
        """The first Stage not yet passed. Steps may only be added / moved at or
        after it — a passed Stage is history."""
        self.ensure_one()
        orders = sorted(set(self.routing_step_ids.mapped("order")))
        for order in orders:
            if not self._stage_complete(order):
                return order
        return orders[-1] if orders else 1

    def _check_route_edit_order(self, order):
        self.ensure_one()
        frontier = self._route_edit_frontier()
        if order < frontier:
            raise UserError(
                _(
                    "ลำดับ %(order)s has already passed — a step may only be placed at "
                    "ลำดับ %(frontier)s or later."
                )
                % {"order": order, "frontier": frontier}
            )

    def _finalize_route_edit(self):
        """Validate the edited Route like ``action_send`` does, then let the engine
        react: activate a step added to the current Stage, or advance when the last
        pending gating step of the Stage was removed."""
        for doc in self:
            live = doc.routing_step_ids.filtered(lambda s: s.state != "skipped")
            if not live.filtered("gating"):
                raise UserError(
                    _(
                        "The Route must keep at least one gating step (เห็นชอบ or "
                        "ลงนาม-อนุมัติ)."
                    )
                )
            if not doc.register_number_id and not live.filtered("verb.issues_number"):
                raise UserError(_("เส้นทางต้องมีขั้นตอนที่ออกเลขที่หนังสือ (เช่น ลงนามในใบปะหน้า)"))
            doc.sudo()._advance_stage()

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

    def _route_edit_unfollow(self, users):
        """Unfollow ``users`` taken off the Route (their to-do subscribed them) once
        the หนังสือ no longer reaches them — read is already gone with their recipient
        rows; this stops the chatter notifications too. The sender stays."""
        self.ensure_one()
        gone = users - self.reached_user_ids - self.sender_user_id
        if gone:
            self.sudo().message_unsubscribe(partner_ids=gone.partner_id.ids)

    # ------------------------------------------------------------------ engine
    def action_pull_back(self, reason=None):
        # ดึงกลับ recreates the Route in the sender's env while still circulating —
        # an engine write, not a route edit.
        return super(
            SarabunDocument, self.with_context(sarabun_route_engine=True)
        ).action_pull_back(reason=reason)

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
        changes = []
        for step in steps.sudo():
            old_users = step.actor_user_ids
            step._snapshot_holders()
            if step.actor_user_ids == old_users:
                continue
            step._check_route_edit_actors()
            step._clear_activities()
            step._schedule_activities()
            step._route_edit_revoke_former()
            changes.append(
                _("%(step)s: %(old)s → %(new)s")
                % {
                    "step": step.name,
                    "old": ", ".join(old_users.mapped("name")) or "-",
                    "new": ", ".join(step.actor_user_ids.mapped("name")),
                }
            )
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
