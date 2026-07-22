from datetime import timedelta

from odoo import api, fields, models

TODO_CATEGORIES = [
    ("execution", "Execution"),
    ("acknowledgement", "Acknowledgement"),
]

# The one category that clears only by acting on the source document. Every
# other Todo — Acknowledgement and uncategorised built-in / hand-scheduled
# activities alike — is dismissable per-user with "Mark as Read" (ADR-0003,
# ADR-0006). Kept as a constant so the "readable?" test lives in one place.
SOURCE_CLEARED_CATEGORY = "execution"


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    todo_category = fields.Selection(
        TODO_CATEGORIES,
        string="Todo Category",
        help="Behavioural category of Todos created from this activity type. "
        "Execution clears by acting on the source; Acknowledgement (and any "
        "uncategorised activity) can be dismissed with 'Mark as Read'.",
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
        help="Set on the activity type and auto-filled here. It only refines "
        "behaviour — Execution Todos clear at the source, everything else is "
        "dismissable with 'Mark as Read' — it does not decide whether the "
        "activity appears in the inbox (every assigned activity does; ADR-0006).",
    )

    @api.depends("activity_type_id")
    def _compute_todo_category(self):
        """Mirror the type's category. Left blank (not defaulted) for types that
        set none: an uncategorised activity still shows in the inbox and clears
        like an Acknowledgement, but keeping it False is what scopes history and
        notifications to real workflow Todos (ADR-0006)."""
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
        # Every assigned activity is in someone's inbox now (ADR-0006), so the
        # badge must react to all of them, not only categorised Todos.
        activities._todo_notify()
        return activities

    def write(self, vals):
        # A write can move an activity between inboxes (reassigning user_id) or
        # re-route a group Todo (role/unit, in the role-in-unit layer). Ping the
        # recipients before the change and after it, so the old and new owners'
        # badges refresh live — not only on reload.
        before = self._todo_recipient_partners()
        res = super().write(vals)
        after = self._todo_recipient_partners()
        partners = before | after
        if partners:
            self._todo_notify(partners)
        return res

    def unlink(self):
        # Capture recipients before the records vanish (badge goes down).
        partners = self._todo_recipient_partners()
        res = super().unlink()
        self._todo_notify(partners)
        return res

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_mark_read(self):
        """Dismiss a Todo for the current user only (ADR-0003): anything that is
        not an Execution Todo — Acknowledgement or uncategorised alike.

        Category-gated server-side so the rule holds beyond the view's attrs.
        """
        self.env["todo.read"]._mark_read(
            self.filtered(lambda a: a.todo_category != SOURCE_CLEARED_CATEGORY)
        )
        self._todo_notify(self.env.user.partner_id)
        return True

    def action_mark_unread(self):
        """Undo a dismissal — bring a read Todo back for me (anything that is not
        an Execution Todo)."""
        self.env["todo.read"]._mark_unread(
            self.filtered(lambda a: a.todo_category != SOURCE_CLEARED_CATEGORY)
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
    # Retention (ADR-0003): read dismissable Todos (Acknowledgement +
    # uncategorised) are garbage collected once older than a configurable
    # threshold (default 180 days).
    # ------------------------------------------------------------------
    @api.model
    def _gc_read_dismissed_todos(self):
        days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_activity_todo.dismissed_retention_days", 180)
        )
        threshold = fields.Datetime.now() - timedelta(days=days)
        # Personal Todos only: a group Todo is one shared record, so one member's
        # read receipt must not delete it for the whole group (ADR-0003). Group
        # dismissable Todos are not auto-GC'd on first-reader-read.
        # "!= execution" also matches uncategorised (NULL) read Todos in Odoo.
        stale = self.search(
            [
                ("todo_category", "!=", SOURCE_CLEARED_CATEGORY),
                ("user_id", "!=", False),
                ("create_date", "<", threshold),
                ("read_ids", "!=", False),
            ]
        )
        stale.unlink()
        return len(stale)
