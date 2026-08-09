from odoo import fields, models
from odoo.tests.common import TransactionCase, tagged


class TodoHostRoleUnit(models.Model):
    """Throwaway host with mail.activity.mixin to exercise role-in-unit group
    routing without any business deps."""

    _name = "test.todo.host.role.unit"
    _description = "Test Todo Host (role-in-unit)"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    operating_unit_id = fields.Many2one("operating.unit")


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

        cls.type_ack = cls.env["mail.activity.type"].create(
            {
                "name": "Test Acknowledgement",
                "todo_category": "acknowledgement",
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
            activity_type_id=self.type_ack.id,
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

    def test_autofill_ou_from_source_on_schedule(self):
        """Scheduling a group Todo without an OU inherits the source record's OU
        (ADR-0002): callers pass only the role."""
        self.rec.operating_unit_id = self.ou
        act = self.rec.activity_schedule(
            activity_type_id=self.type_ack.id,
            responsible_role_id=self.role.id,
        )
        self.assertEqual(
            act.operating_unit_id,
            self.ou,
            "activity should inherit the source record's OU",
        )
        self.assertFalse(act.user_id, "still a group Todo")

    def test_autofill_ou_on_chatter_create(self):
        """A plain activity created from the chatter (personal, no role) also
        picks up the source record's OU so history / grouping stay correct."""
        self.rec.operating_unit_id = self.ou
        act = self.env["mail.activity"].create(
            {
                "activity_type_id": self.type_ack.id,
                "res_model_id": self.env["ir.model"]
                ._get("test.todo.host.role.unit")
                .id,
                "res_id": self.rec.id,
                "user_id": self.officer.id,
            }
        )
        self.assertEqual(act.operating_unit_id, self.ou)

    def test_explicit_ou_is_not_overwritten(self):
        """An OU passed by the caller wins over the source record's OU."""
        ou2 = self.env["operating.unit"].create(
            {
                "name": "Test OU 2",
                "code": "TST-OU2",
                "partner_id": self.env.company.partner_id.id,
            }
        )
        self.rec.operating_unit_id = ou2
        act = self._schedule_group()  # passes operating_unit_id=self.ou
        self.assertEqual(act.operating_unit_id, self.ou)

    def test_ou_follows_source_change(self):
        """Moving the source record to another OU re-routes its open group Todos
        live: the old OU's holder drops out, the new OU's holder sees it."""
        act = self._schedule_group()
        seen = self.Activity.with_user(self.officer).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertEqual(seen, act, "officer (in self.ou) sees it first")

        ou2 = self.env["operating.unit"].create(
            {
                "name": "Test OU 2",
                "code": "TST-OU2",
                "partner_id": self.env.company.partner_id.id,
            }
        )
        officer2 = self.env["res.users"].create(
            {
                "name": "Officer 2",
                "login": "role_unit_officer_ou2",
                "groups_id": [(4, self.env.ref("base.group_user").id)],
                "role_line_ids": [(0, 0, {"role_id": self.role.id})],
            }
        )
        ou2.sudo().write({"user_ids": [(4, officer2.id)]})

        # Source moves OU → the cache on the open activity must follow.
        self.rec.operating_unit_id = ou2
        self.assertEqual(
            act.operating_unit_id, ou2, "activity OU must track the source"
        )
        gone = self.Activity.with_user(self.officer).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertFalse(gone, "officer in the old OU drops out")
        now_seen = self.Activity.with_user(officer2).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertEqual(now_seen, act, "officer in the new OU picks it up")

    def test_cleared_source_ou_keeps_routing(self):
        """Clearing the source's OU must not wipe the activity's: a group Todo
        with neither assignee nor unit would be routed to nobody."""
        self.rec.operating_unit_id = self.ou
        act = self._schedule_group()
        self.rec.operating_unit_id = False
        self.assertEqual(act.operating_unit_id, self.ou, "keeps the last known OU")
        seen = self.Activity.with_user(self.officer).search(
            [("is_my_todo", "=", True), ("id", "=", act.id)]
        )
        self.assertEqual(seen, act, "officer still sees the group Todo")

    def test_gc_keeps_shared_group_todo(self):
        """Retention GC must never delete a shared group Todo on one member's
        read (ADR-0003)."""
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_activity_todo.dismissed_retention_days", "-1"
        )
        group = self._schedule_group()
        self.env["todo.read"].create(
            {"activity_id": group.id, "user_id": self.officer.id}
        )
        self.Activity._gc_read_dismissed_todos()
        self.assertTrue(
            group.exists(), "shared group Todo must survive one member's read"
        )
