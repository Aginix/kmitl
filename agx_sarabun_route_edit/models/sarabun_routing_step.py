"""Route-edit guards on the live steps (ADR-0018).

Apply only to a USER edit of a circulating หนังสือ (``_is_route_edit``) — engine
writes pass untouched. What an editor may do:

* waiting step — change verb / ลำดับ / CC / target, or delete it;
* active step — change only the target (its to-dos move to the new holders), or
  delete it;
* done / skipped / originator step — nothing (signatures never change);
* add a step — as a waiting ``direct`` insertion (so Reset drops it, ADR-0011).

Steps may only be placed after the last Stage already passed. A person taken
off a step loses access to the หนังสือ: their recipient row — the reach ledger that
keys read (ADR-0013) — is deleted and they are unfollowed, unless another step (or a
prior attempt) still reaches them or they sent it. Every edit is logged to the
document chatter.
"""

from odoo import _, api, models
from odoo.exceptions import UserError

TARGET_FIELDS = {"target_mode", "position_id", "employee_id", "department_id"}
SHAPE_FIELDS = TARGET_FIELDS | {"verb", "order", "for_info"}


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    # ------------------------------------------------------------------ helpers
    def _route_edit_values(self):
        """The step's editable shape, rendered for the chatter diff."""
        self.ensure_one()
        return {
            _("ลำดับ"): str(self.order),
            _("การดำเนินการ"): self.verb.name or "",
            _("สำเนาเรียน"): _("Yes") if self.for_info else _("No"),
            _("เป้าหมาย"): self.target_name or "",
        }

    def _route_edit_target(self):
        self.ensure_one()
        return (
            self.target_mode,
            self.position_id,
            self.employee_id,
            self.department_id,
        )

    def _check_route_edit_actors(self):
        """An active step whose target resolves to nobody would strand the หนังสือ
        (personnel without a linked user cannot act — ADR-0005)."""
        for step in self:
            if not step.actor_user_ids:
                raise UserError(
                    _(
                        "%s has no holder with a user account — the step would have "
                        "nobody to act on it."
                    )
                    % step.name
                )

    def _route_edit_reresolve(self):
        """Re-resolve these active steps to their current target (re-target / holder
        refresh): re-snapshot the actors, move the to-dos to them and revoke the
        former holders' access. The engine half of มอบหมาย, without stamping a
        disposition; runs sudo like the act_on_step transitions. Returns
        ``{step: former actors}`` for the steps whose actors changed."""
        changed = {}
        for step in self.sudo():
            former = step.actor_user_ids
            step._snapshot_holders()
            if step.actor_user_ids != former:
                changed[step] = former
        steps = self.sudo().browse([step.id for step in changed])
        steps._check_route_edit_actors()
        steps._clear_activities()
        steps._schedule_activities()
        for step in steps:
            step.document_id._route_edit_revoke(
                step.recipient_ids.filtered(
                    lambda r, step=step: r.user_id not in step.actor_user_ids
                )
            )
        return changed

    def _check_route_edit_editable(self):
        for step in self:
            if step.is_originator or step.state in ("done", "skipped"):
                raise UserError(
                    _("%s has already been acted on — it cannot be changed or removed.")
                    % step.name
                )

    def _route_edit_log(self, body):
        self.ensure_one()
        self.document_id.message_post(
            body=_("Route edited by %(user)s — %(body)s")
            % {
                "user": self.env.user.display_name,
                "body": body,
            }
        )

    # ------------------------------------------------------------------ ORM
    @api.model_create_multi
    def create(self, vals_list):
        Doc = self.env["sarabun.document"]
        edit_docs = Doc
        for vals in vals_list:
            doc = Doc.browse(vals.get("document_id"))
            if doc and doc._is_route_edit():
                doc._check_route_edit_access()
                doc._check_route_edit_order(vals.get("order", 1))
                vals.update(
                    state="waiting",
                    created_by_disposition="direct",
                    attempt_seq=doc.attempt_seq or 1,
                )
                edit_docs |= doc
        steps = super().create(vals_list)
        for step in steps.filtered(lambda s: s.document_id in edit_docs):
            step._route_edit_log(_("added %s") % step.name)
        edit_docs._finalize_route_edit()
        return steps

    def write(self, vals):
        edits = self.browse()
        if SHAPE_FIELDS & set(vals):
            edits = self.filtered(lambda s: s.document_id._is_route_edit())
        if not edits:
            return super().write(vals)
        edits.document_id._check_route_edit_access()
        edits._check_route_edit_editable()
        if edits.filtered(lambda s: s.state == "active") and set(vals) - TARGET_FIELDS:
            raise UserError(
                _("Only the target (ผู้ดำเนินการ) of an active step can be changed.")
            )
        if "order" in vals:
            for doc in edits.document_id:
                doc._check_route_edit_order(vals["order"])
        before = {step: step._route_edit_values() for step in edits}
        targets = {step: step._route_edit_target() for step in edits}
        res = super().write(vals)
        edits.filtered(
            lambda s: s.state == "active" and s._route_edit_target() != targets[s]
        )._route_edit_reresolve()
        for step in edits:
            after = step._route_edit_values()
            diff = [
                "%s: %s → %s" % (label, before[step][label], value)
                for label, value in after.items()
                if before[step][label] != value
            ]
            if diff:
                step._route_edit_log("%s: %s" % (step.name, ", ".join(diff)))
        edits.document_id._finalize_route_edit()
        return res

    def unlink(self):
        edits = self.filtered(lambda s: s.document_id._is_route_edit())
        if not edits:
            return super().unlink()
        docs = edits.document_id
        docs._check_route_edit_access()
        edits._check_route_edit_editable()
        for step in edits:
            step._route_edit_log(_("removed %s") % step.name)
            # Its recipients are taken off the Route: they lose their read.
            step.document_id._route_edit_revoke(step.recipient_ids)
        edits.sudo()._clear_activities()
        res = super().unlink()
        docs._finalize_route_edit()
        return res
