from odoo import fields, models


class ResUsersTodoNotifyRule(models.Model):
    """Per-user override for group-Todo notification per activity type.

    Default behaviour without any rule = the user's global notification OU
    scope (``res.users.todo_notify_operating_unit_ids``). A rule overrides
    that for one activity type: the rule's own ``operating_unit_ids``
    determines which OUs trigger a notification for that type.

    Empty OU list on a rule = mute (no notifications for that type).
    """

    _name = "res.users.todo.notify.rule"
    _description = "Todo Notification Rule (per activity type)"

    user_id = fields.Many2one(
        "res.users", required=True, ondelete="cascade", index=True
    )
    activity_type_id = fields.Many2one(
        "mail.activity.type",
        required=True,
        ondelete="cascade",
        string="Activity Type",
    )
    operating_unit_ids = fields.Many2many(
        "operating.unit",
        "res_users_todo_notify_rule_ou_rel",
        "rule_id",
        "operating_unit_id",
        string="Operating Units",
        help="Receive notifications for this activity type only from these "
        "OUs. Leave empty to mute this type entirely.",
    )

    _sql_constraints = [
        (
            "user_type_uniq",
            "unique(user_id, activity_type_id)",
            "One rule per (user, activity type).",
        ),
    ]
