from odoo import fields, models
from odoo.tests.common import TransactionCase, tagged


class TodoHost(models.Model):
    """A throwaway host carrying mail.activity.mixin to exercise the core Todo
    read-state / logging / retention logic without any business deps."""

    _name = "test.todo.host"
    _description = "Test Todo Host"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()


@tagged("post_install", "-at_install")
class TestMailActivityTodo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        TodoHost._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr, ["test.todo.host"], {"module": "mail_activity_todo"}
        )
        cls.Host = cls.env["test.todo.host"]
        cls.Activity = cls.env["mail.activity"]
        cls.Read = cls.env["todo.read"]
        cls.Log = cls.env["todo.log"]

        cls.type_fyi = cls.env["mail.activity.type"].create(
            {
                "name": "Test FYI",
                "todo_category": "fyi",
                "res_model": "test.todo.host",
            }
        )
        cls.type_exec = cls.env["mail.activity.type"].create(
            {
                "name": "Test Execution",
                "todo_category": "execution",
                "res_model": "test.todo.host",
            }
        )

        cls.user = cls.env["res.users"].create(
            {
                "name": "Todo User",
                "login": "mail_activity_todo_user",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        cls.other = cls.env["res.users"].create(
            {
                "name": "Other User",
                "login": "mail_activity_todo_other",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        cls.rec = cls.Host.create({"name": "host-1"})

    # ------------------------------------------------------------------
    def test_personal_schedule_keeps_user(self):
        act = self.rec.activity_schedule(
            summary="x",
            activity_type_id=self.type_exec.id,
            user_id=self.user.id,
        )
        self.assertEqual(act.user_id, self.user)
        self.assertTrue(act.with_user(self.user).is_my_todo)
        self.assertFalse(act.with_user(self.other).is_my_todo)

    def test_action_done_logs_one_history_row(self):
        act = self.rec.activity_schedule(
            summary="p", activity_type_id=self.type_fyi.id, user_id=self.user.id
        )
        before = self.Log.search_count([])
        act.action_feedback()
        self.assertEqual(self.Log.search_count([]) - before, 1)
        log = self.Log.search([], order="id desc", limit=1)
        self.assertEqual(log.todo_category, "fyi")
        self.assertEqual(log.user_id, self.user)

    def test_mark_read_idempotent_and_per_user(self):
        act = self.rec.activity_schedule(
            summary="fyi", activity_type_id=self.type_fyi.id, user_id=self.user.id
        )
        act.with_user(self.user).action_mark_read()
        act.with_user(self.user).action_mark_read()
        self.assertEqual(
            self.Read.search_count(
                [("activity_id", "=", act.id), ("user_id", "=", self.user.id)]
            ),
            1,
            "mark-read must be idempotent",
        )
        self.assertTrue(act.with_user(self.user).is_read_by_me)
        self.assertFalse(
            act.with_user(self.other).is_read_by_me,
            "read state is per-user",
        )

    def test_mark_read_ignores_non_readable_category(self):
        """Execution/Approval Todos cannot be dismissed (ADR-0003)."""
        act = self.rec.activity_schedule(
            summary="exec", activity_type_id=self.type_exec.id, user_id=self.user.id
        )
        act.with_user(self.user).action_mark_read()
        self.assertEqual(
            self.Read.search_count([("activity_id", "=", act.id)]),
            0,
            "execution Todos must not get a read receipt",
        )

    def test_recipient_partners_personal(self):
        """Bus recipients for a personal Todo = its assignee."""
        personal = self.rec.activity_schedule(
            summary="p", activity_type_id=self.type_fyi.id, user_id=self.user.id
        )
        self.assertEqual(
            personal._todo_recipient_partners(), self.user.partner_id
        )

    def test_gc_personal_read_fyi(self):
        """Retention GC removes read personal FYI past the threshold."""
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_activity_todo.fyi_retention_days", "-1"
        )
        personal = self.rec.activity_schedule(
            summary="p", activity_type_id=self.type_fyi.id, user_id=self.user.id
        )
        self.Read.create({"activity_id": personal.id, "user_id": self.user.id})
        self.Activity._gc_read_fyi_todos()
        self.assertFalse(personal.exists(), "read personal FYI should be GC'd")
