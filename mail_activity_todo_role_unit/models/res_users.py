from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    todo_role_ids = fields.Many2many(
        "res.users.role",
        compute="_compute_todo_role_ids",
        compute_sudo=True,
        string="Todo Roles",
        help="Roles the user holds, exposed without ERP-manager rights so Todo "
        "routing (inbox domain + record rules) can read them.",
    )

    # ------------------------------------------------------------------
    # Notification scope (ADR-0007) — separate from view scope.
    # View scope (operating_unit_ids) says "which OUs I can see"; a Manager OU
    # or *_access_all group expands it wide. Notification scope narrows the
    # group-Todo firehose back down to what the user is actually accountable
    # for. Empty = default to view scope (backward-compat with ADR-0002).
    # ------------------------------------------------------------------
    todo_notify_operating_unit_ids = fields.Many2many(
        "operating.unit",
        "res_users_todo_notify_ou_rel",
        "user_id",
        "operating_unit_id",
        string="Notify Only for These Operating Units",
        help="Restrict group-Todo notifications to these OUs (must be a subset "
        "of your allowed OUs). Leave empty to receive from every OU you can "
        "see — the default that matches the pre-ADR-0007 behaviour.",
    )
    todo_notify_rule_ids = fields.One2many(
        "res.users.todo.notify.rule",
        "user_id",
        string="Per-type Notification Rules",
        help="Override the OU scope for specific activity types: widen back to "
        "every OU (all_ous), or mute the type entirely.",
    )

    @api.depends("role_ids")
    def _compute_todo_role_ids(self):
        for user in self:
            user.todo_role_ids = user.sudo().role_ids.ids

    def _my_todo_count_domain(self):
        """Systray badge counts only primary Todos (ADR-0007).

        A manager with wide view scope still sees oversight Todos in the
        secondary tab, but the badge reflects work they are accountable for —
        not everything they could look at.
        """
        return super()._my_todo_count_domain() + [
            ("is_my_primary_todo", "=", True)
        ]

    def _my_oversight_todo_domain(self):
        """Group Todos I can see but that fall outside my notification scope
        (ADR-0007). Empty for users whose view scope equals their notification
        scope — the default — which is what hides the secondary tab.
        """
        return [
            ("is_my_todo", "=", True),
            ("is_my_primary_todo", "=", False),
            ("is_read_by_me", "=", False),
        ]

    @api.model
    def get_my_oversight_todo_count(self):
        """Simple counter used by the inbox view to hide the Oversight tab when
        empty (Q8-ข). Kept separate from ``get_my_todo_count`` because the tab
        only needs a boolean-ish signal, not the full per-model buckets."""
        return self.env["mail.activity"].search_count(
            self._my_oversight_todo_domain()
        )
