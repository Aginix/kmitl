from datetime import timedelta

from odoo import fields, models
from odoo.tests.common import TransactionCase, tagged


class TodoHost(models.Model):
    """A throwaway host carrying mail.activity.mixin to exercise the Todo
    routing/read-state/logging logic without procurement_plan's heavy deps."""

    _name = "test.kmitl.todo.host"
    _description = "Test Todo Host"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()


@tagged("post_install", "-at_install")
class TestKmitlTodo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        TodoHost._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr, ["test.kmitl.todo.host"], {"module": "kmitl_todo"}
        )
        cls.Host = cls.env["test.kmitl.todo.host"]
        cls.Activity = cls.env["mail.activity"]
        cls.Read = cls.env["kmitl.todo.read"]
        cls.Log = cls.env["kmitl.todo.log"]

        cls.type_fyi = cls.env["mail.activity.type"].create(
            {
                "name": "Test FYI",
                "todo_category": "fyi",
                "res_model": "test.kmitl.todo.host",
            }
        )
        cls.type_exec = cls.env["mail.activity.type"].create(
            {
                "name": "Test Execution",
                "todo_category": "execution",
                "res_model": "test.kmitl.todo.host",
            }
        )

        cls.role = cls.env["res.users.role"].create({"name": "Test Plan Officer"})
        cls.ou = cls.env["operating.unit"].create(
            {
                "name": "Test OU",
                "code": "TST-OU",
                "partner_id": cls.env.company.partner_id.id,
            }
        )
        cls.officer = cls.env["res.users"].create(
            {
                "name": "Officer",
                "login": "kmitl_todo_officer",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )
        cls.outsider = cls.env["res.users"].create(
            {
                "name": "Outsider",
                "login": "kmitl_todo_outsider",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        # OU membership is the operating.unit.user_ids M2M (set from the OU side).
        cls.ou.sudo().write({"user_ids": [(4, cls.officer.id)]})
        cls.rec = cls.Host.create({"name": "host-1"})

    # ------------------------------------------------------------------
    def _schedule_group(self):
        return self.rec.activity_schedule(
            "kmitl_todo.mail_activity_procurement_plan_fill",
            responsible_role_id=self.role.id,
            operating_unit_id=self.ou.id,
        )

    def test_group_schedule_has_no_user(self):
        """A group Todo (role + OU, no user) must stay unassigned (ADR-0002)."""
        followers_before = self.rec.message_partner_ids
        act = self._schedule_group()
        self.assertFalse(act.user_id, "group Todo must have no single assignee")
        self.assertEqual(act.responsible_role_id, self.role)
        self.assertEqual(act.operating_unit_id, self.ou)
        # ...and scheduling must NOT subscribe the scheduler as a follower.
        self.assertEqual(
            self.rec.message_partner_ids,
            followers_before,
            "scheduling a group Todo must not change followers",
        )

    def test_personal_schedule_keeps_user(self):
        act = self.rec.activity_schedule(
            summary="x",
            activity_type_id=self.type_exec.id,
            user_id=self.officer.id,
        )
        self.assertEqual(act.user_id, self.officer)

    def test_is_my_todo_role_in_unit(self):
        """A user holding the role in the OU sees the unclaimed group Todo;
        an outsider does not (ADR-0002)."""
        act = self._schedule_group()
        as_officer = self.Activity.with_user(self.officer).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertEqual(as_officer, act, "officer should see the group Todo")
        as_outsider = self.Activity.with_user(self.outsider).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertFalse(as_outsider, "outsider must not see the group Todo")

    def test_claim_removes_from_other_inboxes(self):
        """Claiming a group Todo (sets user_id) drops it from other members."""
        act = self._schedule_group()
        act.with_user(self.officer).action_claim()
        self.assertEqual(act.user_id, self.officer)
        # A second officer in the same role+OU should no longer see it.
        other = self.env["res.users"].create(
            {
                "name": "Officer 2",
                "login": "kmitl_todo_officer2",
                "groups_id": [(4, self.env.ref("base.group_user").id)],
                "role_line_ids": [(0, 0, {"role_id": self.role.id})],
            }
        )
        self.ou.sudo().write({"user_ids": [(4, other.id)]})
        seen = self.Activity.with_user(other).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertFalse(seen, "claimed Todo should leave colleagues' inboxes")

    def test_action_done_logs_one_history_row(self):
        act = self._schedule_group()
        before = self.Log.search_count([])
        act.action_feedback()
        self.assertEqual(self.Log.search_count([]) - before, 1)
        log = self.Log.search([], order="id desc", limit=1)
        self.assertEqual(log.todo_category, "fyi")
        self.assertEqual(log.responsible_role_id, self.role)

    def test_mark_read_idempotent_and_per_user(self):
        act = self.rec.activity_schedule(
            summary="fyi", activity_type_id=self.type_fyi.id, user_id=self.officer.id
        )
        act.with_user(self.officer).action_mark_read()
        act.with_user(self.officer).action_mark_read()
        self.assertEqual(
            self.Read.search_count(
                [("activity_id", "=", act.id), ("user_id", "=", self.officer.id)]
            ),
            1,
            "mark-read must be idempotent",
        )
        self.assertTrue(act.with_user(self.officer).is_read_by_me)
        self.assertFalse(
            act.with_user(self.outsider).is_read_by_me,
            "read state is per-user",
        )

    def test_mark_read_ignores_non_readable_category(self):
        """Execution/Approval Todos cannot be dismissed (ADR-0003)."""
        act = self.rec.activity_schedule(
            summary="exec", activity_type_id=self.type_exec.id, user_id=self.officer.id
        )
        act.with_user(self.officer).action_mark_read()
        self.assertEqual(
            self.Read.search_count([("activity_id", "=", act.id)]),
            0,
            "execution Todos must not get a read receipt",
        )

    def test_gc_personal_only(self):
        """Retention GC removes read personal FYI, never shared group Todos."""
        self.env["ir.config_parameter"].sudo().set_param(
            "kmitl_todo.fyi_retention_days", "-1"
        )
        personal = self.rec.activity_schedule(
            summary="p", activity_type_id=self.type_fyi.id, user_id=self.officer.id
        )
        group = self._schedule_group()
        # both read by someone
        self.Read.create({"activity_id": personal.id, "user_id": self.officer.id})
        self.Read.create({"activity_id": group.id, "user_id": self.officer.id})
        self.Activity._gc_read_fyi_todos()
        self.assertFalse(personal.exists(), "read personal FYI should be GC'd")
        self.assertTrue(
            group.exists(), "shared group Todo must survive one member's read"
        )
