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

    todo_category = fields.Selection(
        TODO_CATEGORIES,
        string="Todo Category",
        compute="_compute_todo_category",
        store=True,
        index=True,
        readonly=False,
        help="Defaults from the activity type. Set it on a manually scheduled "
        "activity to turn it into a Todo that lands in your inbox.",
    )

    @api.depends("activity_type_id")
    def _compute_todo_category(self):
        """Default the category from the type, but leave it user-overridable so a
        manually scheduled activity can be categorised into the Todo inbox."""
        for activity in self:
            activity.todo_category = activity.activity_type_id.todo_category

    read_ids = fields.One2many("todo.read", "activity_id", string="Read receipts")
    is_my_todo = fields.Boolean(
        string="Is My Todo",
        compute="_compute_is_my_todo",
        search="_search_is_my_todo",
        help="Technical: addressed to the current user. The core engine matches "
        "personal Todos (user_id); the role-in-unit layer extends this to group "
        "Todos.",
    )
    is_read_by_me = fields.Boolean(
        string="Read",
        compute="_compute_is_read_by_me",
        search="_search_is_read_by_me",
    )

    # ------------------------------------------------------------------
    # is_my_todo  (the shared inbox domain — extension point)
    # ------------------------------------------------------------------
    def _my_todo_domain(self):
        """Domain on mail.activity selecting Todos addressed to the current user.

        The core engine selects personal (user_id) Todos. Layers that add group
        routing (e.g. role-in-unit, ADR-0002) override this to OR-in their own
        recipient branch.
        """
        return [("user_id", "=", self.env.user.id)]

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
            self.env["todo.read"]
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
            self.env["todo.read"].sudo().search([("user_id", "=", self.env.uid)])
        )
        ids = read.activity_id.ids
        positive = (operator in ("=", "==") and value) or (
            operator == "!=" and not value
        )
        return [("id", "in", ids)] if positive else [("id", "not in", ids)]

    # ------------------------------------------------------------------
    # Live updates (bus.bus) — refresh the systray badge in real time
    # ------------------------------------------------------------------
    def _todo_recipient_partners(self):
        """Partners whose Todo inbox is affected by these activities. The core
        engine resolves the personal assignee; layers extend this (e.g. live
        role-in-unit members for group Todos — ADR-0002)."""
        partners = self.env["res.partner"]
        for act in self:
            if act.user_id:
                partners |= act.user_id.partner_id
        return partners

    def _todo_notify(self, partners=None):
        """Ping affected users' bus channels so their systray badge refetches."""
        if partners is None:
            partners = self._todo_recipient_partners()
        for partner in partners:
            self.env["bus.bus"]._sendone(
                partner, "mail_activity_todo/updated", {"refresh": True}
            )

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        # Only Todo-categorised activities drive the inbox; skip the rest.
        activities.filtered("todo_category")._todo_notify()
        return activities

    def write(self, vals):
        # A write can move a Todo between inboxes (reassigning user_id), turn an
        # activity into/out of a Todo (todo_category), or re-route a group Todo
        # (role/unit, in the role-in-unit layer). Ping both the recipients before
        # the change and after it, so the old and new owners' badges refresh live
        # — not only on reload.
        before = self.filtered("todo_category")._todo_recipient_partners()
        res = super().write(vals)
        after = self.filtered("todo_category")._todo_recipient_partners()
        partners = before | after
        if partners:
            self._todo_notify(partners)
        return res

    def unlink(self):
        # Capture recipients before the records vanish (badge goes down).
        partners = self.filtered("todo_category")._todo_recipient_partners()
        res = super().unlink()
        self._todo_notify(partners)
        return res

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_mark_read(self):
        """Dismiss FYI/Acknowledgement Todos for the current user only (ADR-0003).

        Category-gated server-side so the rule holds beyond the view's attrs.
        """
        self.env["todo.read"]._mark_read(
            self.filtered(lambda a: a.todo_category in READABLE_CATEGORIES)
        )
        self._todo_notify(self.env.user.partner_id)
        return True

    def action_mark_unread(self):
        """Undo a dismissal — bring FYI/Acknowledgement Todos back for me."""
        self.env["todo.read"]._mark_unread(
            self.filtered(lambda a: a.todo_category in READABLE_CATEGORIES)
        )
        self._todo_notify(self.env.user.partner_id)
        return True

    def _action_done(self, feedback=False, attachment_ids=None):
        # Snapshot completed Todos to history before core unlinks them (ADR-0004).
        self.env["todo.log"]._log_completed(self.filtered("todo_category"))
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
            .get_param("mail_activity_todo.fyi_retention_days", 180)
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
