from odoo import _, fields, models

# Project states that mark a KRIS project as *closed* — no further handler
# action is expected once one of these is reached, so any open assignment
# To-Do on the record is cleared to keep assignee inboxes tidy.
CLOSE_STATES = ("done", "cancel", "terminated", "conditional_close")


class KrisProject(models.Model):
    _name = "kris.project"
    _inherit = ["kris.project", "assignment.mixin"]

    _assign_user_group = "kris_project.group_kris_project_officer"
    _assign_manager_group = "kris_project.group_kris_project_manager"

    # New field: the KRIS Officer currently handling the project. Distinct
    # from ``user_id`` ("Responsible" — the fixed owner/creator); see the
    # module ADR-0001 and kris_project/CONTEXT.md for the semantic split.
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Assigned Officer",
        copy=False,
        tracking=True,
        index=True,
    )

    def _assignment_activity_summary(self):
        return _("Assigned as responsible KRIS officer")

    # No takeover: manager-only reassign. Deliberately not overriding
    # ``_assignment_takeover_param`` — the base default returns ``None``,
    # which the mixin reads as "takeover feature disabled".

    def write(self, vals):
        # Bulk-close open assignment To-Dos when the project transitions
        # into a closed state, catching every entry point (direct write,
        # action_cancel, and the state wizard which writes state=... via
        # the ORM).
        close_targets = self.env["kris.project"]
        if "state" in vals and vals["state"] in CLOSE_STATES:
            close_targets = self.filtered(lambda r: r.state != vals["state"])
        res = super().write(vals)
        if close_targets:
            close_targets._assignment_close_activity()
        return res

    def _assignment_close_activity(self):
        """Bulk-close every open assignment To-Do on this record.

        The base ``_assignment_clear_activity(user)`` is per-user; project
        close is state-driven and the actor may not be the assignee, so we
        sweep every open activity of the assignment type regardless of who
        scheduled it. Mirrors ``disbursement_assignment``'s helper of the
        same name.
        """
        activity_type = self.env.ref(self._assignment_activity_xmlid())
        summary = self._assignment_activity_summary()
        for rec in self:
            stale = rec.sudo().activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type and a.summary == summary
            )
            stale.unlink()
