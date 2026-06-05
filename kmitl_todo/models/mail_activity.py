from datetime import timedelta

from odoo import api, fields, models

TODO_CATEGORIES = [
    ("approval", "Approval"),
    ("execution", "Execution"),
    ("acknowledgement", "Acknowledgement"),
    ("fyi", "FYI"),
]

# Categories the user may dismiss with "Mark as Read" (ADR-0003). The others
# (approval/execution) clear only by acting on the source record.
READABLE_CATEGORIES = ("acknowledgement", "fyi")


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    todo_category = fields.Selection(
        TODO_CATEGORIES,
        string="Todo Category",
        help="Behavioural category of Todos created from this activity type. "
        "Approval/Execution clear by acting on the source; "
        "Acknowledgement/FYI can be dismissed with 'Mark as Read'.",
    )


class MailActivity(models.Model):
    _inherit = "mail.activity"

    # --- Group routing tags: role-in-unit, resolved live (ADR-0002) ---
    responsible_role_id = fields.Many2one(
        "res.users.role",
        string="Responsible Role",
        index=True,
        ondelete="cascade",
        help="When set together with an Operating Unit, this is a group Todo for "
        "everyone holding this role in that unit. Leave empty for a personal Todo.",
    )
    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        index=True,
        ondelete="cascade",
    )
    todo_category = fields.Selection(
        related="activity_type_id.todo_category",
        store=True,
        index=True,
        readonly=True,
    )
    # Group Todos have no single assignee (ADR-0002).
    user_id = fields.Many2one(required=False)

    read_ids = fields.One2many(
        "kmitl.todo.read", "activity_id", string="Read receipts"
    )
    is_my_todo = fields.Boolean(
        string="Is My Todo",
        compute="_compute_is_my_todo",
        search="_search_is_my_todo",
        help="Technical: addressed to the current user, personally (user_id) or "
        "via a role held in one of the user's operating units.",
    )
    is_read_by_me = fields.Boolean(
        string="Read",
        compute="_compute_is_read_by_me",
        search="_search_is_read_by_me",
    )

    # ------------------------------------------------------------------
    # is_my_todo  (the shared inbox domain — ADR-0002)
    # ------------------------------------------------------------------
    def _my_todo_domain(self):
        """Domain on mail.activity selecting Todos addressed to the current user:
        personal (user_id) Todos, plus group Todos for a role held in one of the
        user's operating units that are unclaimed or claimed by this user.
        A group Todo claimed by someone else (Claim) drops out of my inbox.
        """
        user = self.env.user
        role_ids = user.kmitl_role_ids.ids
        ou_ids = user.operating_unit_ids.ids
        personal = [("user_id", "=", user.id)]
        if role_ids and ou_ids:
            return [
                "|",
                ("user_id", "=", user.id),
                "&",
                "&",
                ("responsible_role_id", "in", role_ids),
                ("operating_unit_id", "in", ou_ids),
                ("user_id", "in", [False, user.id]),
            ]
        return personal

    @api.depends_context("uid")
    def _compute_is_my_todo(self):
        mine = self.filtered_domain(self._my_todo_domain())
        for activity in self:
            activity.is_my_todo = activity in mine

    def _search_is_my_todo(self, operator, value):
        positive = (operator in ("=", "==") and value) or (
            operator == "!=" and not value
        )
        domain = self._my_todo_domain()
        return domain if positive else ["!"] + domain

    # ------------------------------------------------------------------
    # is_read_by_me  (per-user read state — ADR-0003)
    # ------------------------------------------------------------------
    @api.depends("read_ids")
    @api.depends_context("uid")
    def _compute_is_read_by_me(self):
        read = (
            self.env["kmitl.todo.read"]
            .sudo()
            .search(
                [("activity_id", "in", self.ids), ("user_id", "=", self.env.uid)]
            )
        )
        read_activity_ids = set(read.activity_id.ids)
        for activity in self:
            activity.is_read_by_me = activity.id in read_activity_ids

    def _search_is_read_by_me(self, operator, value):
        read = (
            self.env["kmitl.todo.read"]
            .sudo()
            .search([("user_id", "=", self.env.uid)])
        )
        ids = read.activity_id.ids
        positive = (operator in ("=", "==") and value) or (
            operator == "!=" and not value
        )
        return [("id", "in", ids)] if positive else [("id", "not in", ids)]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_mark_read(self):
        """Dismiss FYI/Acknowledgement Todos for the current user only (ADR-0003).

        Category-gated server-side so the rule holds beyond the view's attrs.
        """
        self.env["kmitl.todo.read"]._mark_read(
            self.filtered(lambda a: a.todo_category in READABLE_CATEGORIES)
        )
        return True

    def action_mark_unread(self):
        """Undo a dismissal — bring FYI/Acknowledgement Todos back for me."""
        self.env["kmitl.todo.read"]._mark_unread(
            self.filtered(lambda a: a.todo_category in READABLE_CATEGORIES)
        )
        return True

    def action_claim(self):
        """รับเรื่อง — take an unclaimed group Todo as your own so colleagues
        see it is being handled (and it leaves their inbox)."""
        self.filtered(lambda a: a.responsible_role_id and not a.user_id).write(
            {"user_id": self.env.uid}
        )
        return True

    def action_unclaim(self):
        """Release a claimed group Todo back to the role-in-unit."""
        self.filtered("responsible_role_id").write({"user_id": False})
        return True

    def _action_done(self, feedback=False, attachment_ids=None):
        # Snapshot completed Todos to history before core unlinks them (ADR-0004).
        self.env["kmitl.todo.log"]._log_completed(self.filtered("todo_category"))
        return super()._action_done(
            feedback=feedback, attachment_ids=attachment_ids
        )

    # ------------------------------------------------------------------
    # Retention (ADR-0003): read FYI/Acknowledgement Todos are garbage
    # collected once older than a configurable threshold (default 180 days).
    # ------------------------------------------------------------------
    @api.model
    def _gc_read_fyi_todos(self):
        days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("kmitl_todo.fyi_retention_days", 180)
        )
        threshold = fields.Datetime.now() - timedelta(days=days)
        # Personal Todos only: a group Todo is one shared record, so one member's
        # read receipt must not delete it for the whole group (ADR-0003). Group
        # FYI/Ack are not auto-GC'd on first-reader-read.
        stale = self.search(
            [
                ("todo_category", "in", list(READABLE_CATEGORIES)),
                ("user_id", "!=", False),
                ("create_date", "<", threshold),
                ("read_ids", "!=", False),
            ]
        )
        stale.unlink()
        return len(stale)
