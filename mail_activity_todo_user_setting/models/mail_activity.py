from odoo import api, fields, models
from odoo.osv import expression


class MailActivity(models.Model):
    _inherit = "mail.activity"

    is_my_primary_todo = fields.Boolean(
        string="Is My Primary Todo",
        compute="_compute_is_my_primary_todo",
        search="_search_is_my_primary_todo",
        help="Technical: matches the notification-scoped inbox (ADR-0007). "
        "Personal Todos are always primary; group Todos are primary only when "
        "they fall inside the user's notification OU scope.",
    )

    def _my_primary_todo_domain(self):
        """Notification-scoped inbox domain (ADR-0007).

        Personal Todos always pass. Group Todos are matched per activity type:

        1. Type has a rule → use the rule's OU list (empty = muted).
        2. No rule → use the global ``todo_notify_operating_unit_ids``
           (empty = all view-scope OUs, backward-compatible).
        """
        user = self.env.user
        personal = [("user_id", "=", user.id)]
        role_ids = user.todo_role_ids.ids
        view_ou_ids = user.operating_unit_ids.ids
        if not role_ids or not view_ou_ids:
            return personal

        global_ou_ids = (
            user.todo_notify_operating_unit_ids.ids or view_ou_ids
        )
        rules = user.todo_notify_rule_ids
        group_base = [
            ("responsible_role_id", "in", role_ids),
            ("user_id", "in", [False, user.id]),
        ]

        rule_type_ids = rules.activity_type_id.ids

        default_branch = [("operating_unit_id", "in", global_ou_ids)]
        if rule_type_ids:
            default_branch = expression.AND(
                [
                    [("activity_type_id", "not in", rule_type_ids)],
                    default_branch,
                ]
            )

        type_branches = [default_branch]
        for rule in rules:
            rule_ou_ids = rule.operating_unit_ids.ids
            if rule_ou_ids:
                type_branches.append(
                    expression.AND(
                        [
                            [("activity_type_id", "=", rule.activity_type_id.id)],
                            [("operating_unit_id", "in", rule_ou_ids)],
                        ]
                    )
                )

        type_ou = expression.OR(type_branches)
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
