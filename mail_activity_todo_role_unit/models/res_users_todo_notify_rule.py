from odoo import fields, models


class ResUsersTodoNotifyRule(models.Model):
    """Per-user override for group-Todo notification per activity type.

    Default behaviour without any rule = the user's notification OU scope
    (``res.users.todo_notify_operating_unit_ids``). A rule flips one activity
    type out of that default: ``all_ous`` widens it back to every OU the user
    can see, ``mute`` drops it from the primary inbox entirely.
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
    mode = fields.Selection(
        [
            ("all_ous", "รับจากทุกหน่วยงานที่เห็น"),
            ("mute", "ไม่รับแจ้งเตือน (ย้ายไปแท็บอื่นๆ)"),
        ],
        required=True,
        default="all_ous",
        help="all_ous: widen to every OU the user can see, overriding the OU "
        "scope. mute: drop from the primary inbox (still visible under "
        "'Oversight' if the user could see it).",
    )

    _sql_constraints = [
        (
            "user_type_uniq",
            "unique(user_id, activity_type_id)",
            "One rule per (user, activity type).",
        ),
    ]
