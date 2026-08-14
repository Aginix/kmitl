from odoo import api, fields, models
from odoo.osv import expression


class MailActivity(models.Model):
    _inherit = "mail.activity"

    # ADR-0007: primary = personal ∪ group todos matching my notification scope
    # (view scope narrowed by todo_notify_operating_unit_ids and per-type rules).
    # Oversight = is_my_todo AND NOT is_my_primary_todo — group todos I can see
    # but haven't opted in to be notified for.
    is_my_primary_todo = fields.Boolean(
        string="Is My Primary Todo",
        compute="_compute_is_my_primary_todo",
        search="_search_is_my_primary_todo",
        help="Technical: matches the notification-scoped inbox (ADR-0007). "
        "Personal Todos are always primary; group Todos are primary only when "
        "they fall inside the user's notification OU scope (or an all_ous rule).",
    )

    def _my_primary_todo_domain(self):
        """Notification-scoped inbox domain (ADR-0007).

        Personal Todos are always primary (bypass filter). Group Todos are
        primary only when the OU/type combination passes the user's
        notification scope:

        - ``all_ous`` rule on a type → widens back to every view-scope OU.
        - ``mute`` rule on a type → drops from primary entirely.
        - No rule for a type → matches ``todo_notify_operating_unit_ids``
          (falling back to the full view scope when the user has not set one,
          i.e. backward-compatible default).
        """
        user = self.env.user
        personal = [("user_id", "=", user.id)]
        role_ids = user.todo_role_ids.ids
        view_ou_ids = user.operating_unit_ids.ids
        if not role_ids or not view_ou_ids:
            return personal
        notify_ou_ids = (
            user.todo_notify_operating_unit_ids.ids or view_ou_ids
        )
        rules = user.todo_notify_rule_ids
        all_ous_types = rules.filtered(
            lambda r: r.mode == "all_ous"
        ).activity_type_id.ids
        mute_types = rules.filtered(
            lambda r: r.mode == "mute"
        ).activity_type_id.ids
        group_base = [
            ("responsible_role_id", "in", role_ids),
            ("user_id", "in", [False, user.id]),
        ]

        default_branch = [("operating_unit_id", "in", notify_ou_ids)]
        override_types = all_ous_types + mute_types
        if override_types:
            default_branch = expression.AND(
                [
                    [("activity_type_id", "not in", override_types)],
                    default_branch,
                ]
            )
        if all_ous_types:
            widen_branch = expression.AND(
                [
                    [("activity_type_id", "in", all_ous_types)],
                    [("operating_unit_id", "in", view_ou_ids)],
                ]
            )
            type_ou = expression.OR([widen_branch, default_branch])
        else:
            type_ou = default_branch
        group = expression.AND([group_base, type_ou])
        return expression.OR([personal, group])

    @api.depends_context("uid")
    def _compute_is_my_primary_todo(self):
        mine = self.filtered_domain(self._my_primary_todo_domain())
        for activity in self:
            activity.is_my_primary_todo = activity in mine

    def _search_is_my_primary_todo(self, operator, value):
        positive = (operator in ("=", "==") and value) or (
            operator == "!=" and not value
        )
        domain = self._my_primary_todo_domain()
        return domain if positive else ["!"] + domain
