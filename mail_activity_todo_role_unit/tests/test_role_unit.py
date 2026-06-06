from odoo import fields, models
from odoo.tests.common import TransactionCase, tagged


class TodoHostRoleUnit(models.Model):
    """Throwaway host with mail.activity.mixin to exercise role-in-unit group
    routing without any business deps."""

    _name = "test.todo.host.role.unit"
    _description = "Test Todo Host (role-in-unit)"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()


@tagged("post_install", "-at_install")
class TestRoleUnit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        TodoHostRoleUnit._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            ["test.todo.host.role.unit"],
            {"module": "mail_activity_todo_role_unit"},
        )
        cls.Host = cls.env["test.todo.host.role.unit"]
        cls.Activity = cls.env["mail.activity"]
        cls.Log = cls.env["todo.log"]

        cls.type_fyi = cls.env["mail.activity.type"].create(
            {
                "name": "Test FYI",
                "todo_category": "fyi",
                "res_model": "test.todo.host.role.unit",
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
                "login": "role_unit_officer",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )
        cls.outsider = cls.env["res.users"].create(
            {
                "name": "Outsider",
                "login": "role_unit_outsider",
                "groups_id": [(4, cls.env.ref("base.group_user").id)],
            }
        )
        # OU membership is the operating.unit.user_ids M2M (set from the OU side).
        cls.ou.sudo().write({"user_ids": [(4, cls.officer.id)]})
        cls.rec = cls.Host.create({"name": "host-1"})

    def _schedule_group(self):
        return self.rec.activity_schedule(
            activity_type_id=self.type_fyi.id,
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

    def test_is_my_todo_role_in_unit(self):
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
        act = self._schedule_group()
        act.with_user(self.officer).action_claim()
        self.assertEqual(act.user_id, self.officer)
        other = self.env["res.users"].create(
            {
                "name": "Officer 2",
                "login": "role_unit_officer2",
                "groups_id": [(4, self.env.ref("base.group_user").id)],
                "role_line_ids": [(0, 0, {"role_id": self.role.id})],
            }
        )
        self.ou.sudo().write({"user_ids": [(4, other.id)]})
        seen = self.Activity.with_user(other).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertFalse(seen, "claimed Todo should leave colleagues' inboxes")

    def test_action_done_logs_role_in_unit(self):
        act = self._schedule_group()
        before = self.Log.search_count([])
        act.action_feedback()
        self.assertEqual(self.Log.search_count([]) - before, 1)
        log = self.Log.search([], order="id desc", limit=1)
        self.assertEqual(log.responsible_role_id, self.role)
        self.assertEqual(log.operating_unit_id, self.ou)

    def test_recipient_partners_group(self):
        group = self._schedule_group()
        self.assertIn(
            self.officer.partner_id, group._todo_recipient_partners()
        )

    def test_gc_keeps_shared_group_todo(self):
        """Retention GC must never delete a shared group Todo on one member's
        read (ADR-0003)."""
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_activity_todo.fyi_retention_days", "-1"
        )
        group = self._schedule_group()
        self.env["todo.read"].create(
            {"activity_id": group.id, "user_id": self.officer.id}
        )
        self.Activity._gc_read_fyi_todos()
        self.assertTrue(
            group.exists(), "shared group Todo must survive one member's read"
        )
