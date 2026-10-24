from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    can_submit_sarabun = fields.Boolean(
        compute="_compute_can_submit_sarabun",
        help="The current user may create the project approval document: the "
        "project manager, a coordinator, the creator or a project officer.",
    )

    @api.depends_context("uid")
    @api.depends("is_project_owner")
    def _compute_can_submit_sarabun(self):
        is_officer = self.env.user.has_group(
            "kmitl_project.group_kmitl_project_user_all"
        )
        for rec in self:
            rec.can_submit_sarabun = is_officer or rec.is_project_owner

    def _sarabun_submit_guard(self):
        allowed = super()._sarabun_submit_guard()
        if allowed and not self.can_submit_sarabun:
            raise AccessError(
                _(
                    "Only the project manager, a coordinator, the creator or a "
                    "project officer can create the project approval document."
                )
            )
        return allowed

    def action_submit_to_sarabun(self):
        action = super().action_submit_to_sarabun()
        if action:
            self._sync_sarabun_owner_followers()
        return action

    def write(self, vals):
        if "coordinator_ids" not in vals and "manager_id" not in vals:
            return super().write(vals)
        previous = {rec: rec._sarabun_owner_partners() for rec in self}
        res = super().write(vals)
        for rec in self:
            rec._sync_sarabun_owner_followers(previous[rec])
        return res

    def _sarabun_owner_partners(self):
        self.ensure_one()
        return (
            self.manager_id.sudo().user_id
            | self.coordinator_ids
            | self.creating_user_id
        ).partner_id

    def _sync_sarabun_owner_followers(self, previous_partners=None):
        """Make the project's owners followers of its หนังสือ — the follower read
        rule lets them open it (ADR-0013) — and unsubscribe owners who were
        removed from the still-open หนังสือ, except its sender. A finished
        หนังสือ (completed / rejected / cancelled) keeps them: they stay able to
        read what was decided while they owned the project."""
        for rec in self:
            documents = rec._all_sarabun_documents()
            if not documents:
                continue
            owners = rec._sarabun_owner_partners()
            documents.message_subscribe(partner_ids=owners.ids)
            removed = (previous_partners or owners.browse()) - owners
            if removed:
                for document in documents.filtered(
                    lambda d: d.state not in ("completed", "rejected", "cancelled")
                ):
                    document.message_unsubscribe(
                        partner_ids=(removed - document.sender_user_id.partner_id).ids
                    )
