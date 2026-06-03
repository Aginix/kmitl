from odoo import api, fields, models


class KmitlTodoRead(models.Model):
    """Per-user read state for Todos (ADR-0003).

    A group Todo is one shared ``mail.activity`` seen by many users, so "read"
    cannot live on the activity itself. This thin side table records *who* has
    dismissed which activity; the inbox hides the activities the current user
    has read. It never holds Todo content — the activity stays the source of
    truth.
    """

    _name = "kmitl.todo.read"
    _description = "Per-user read state for Todos"

    activity_id = fields.Many2one(
        "mail.activity",
        string="Todo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: self.env.user,
    )
    read_date = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [
        (
            "activity_user_uniq",
            "unique(activity_id, user_id)",
            "A read receipt already exists for this user and Todo.",
        ),
    ]

    @api.model
    def _mark_read(self, activities):
        """Record that the current user has read ``activities`` (idempotent)."""
        already = self.search(
            [
                ("activity_id", "in", activities.ids),
                ("user_id", "=", self.env.uid),
            ]
        )
        to_create = activities - already.activity_id
        return self.create([{"activity_id": act.id} for act in to_create])
