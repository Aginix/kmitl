from odoo import fields, models
from odoo.tests.common import TransactionCase, tagged


class TodoHostScope(models.Model):
    """Throwaway host with mail.activity.mixin to exercise notification scope
    (ADR-0007) without any business deps."""

    _name = "test.todo.host.scope"
    _description = "Test Todo Host (notification scope)"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    operating_unit_id = fields.Many2one("operating.unit")


@tagged("post_install", "-at_install")
class TestNotificationScope(TransactionCase):
    """ADR-0007 — view scope stays wide, notification scope narrows the primary
    inbox and lets Oversight surface the delta.

    We stress a *manager* whose operating_unit_ids is auto-expanded to every OU
    by group_manager_operating_unit — the concrete flooding scenario the ADR
    was written for.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        TodoHostScope._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr,
            ["test.todo.host.scope"],
            {"module": "mail_activity_todo_notify_scope"},
        )
        cls.Host = cls.env["test.todo.host.scope"]
        cls.Activity = cls.env["mail.activity"]

        cls.type_a = cls.env["mail.activity.type"].create(
            {
                "name": "Planning Todo",
                "todo_category": "acknowledgement",
                "res_model": "test.todo.host.scope",
            }
        )
        cls.type_b = cls.env["mail.activity.type"].create(
            {
                "name": "Sarabun Confirmation",
                "todo_category": "acknowledgement",
                "res_model": "test.todo.host.scope",
            }
        )
        cls.role = cls.env["res.users.role"].create({"name": "Planner"})

        partner = cls.env.company.partner_id.id
        cls.ou_a = cls.env["operating.unit"].create(
            {"name": "OU A", "code": "OU-A", "partner_id": partner}
        )
        cls.ou_b = cls.env["operating.unit"].create(
            {"name": "OU B", "code": "OU-B", "partner_id": partner}
        )
        cls.ou_c = cls.env["operating.unit"].create(
            {"name": "OU C", "code": "OU-C", "partner_id": partner}
        )

        # Manager: holds group_manager_operating_unit → operating_unit_ids
        # expands to every OU (the flooding scenario).
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Manager",
                "login": "scope_manager",
                "groups_id": [
                    (4, cls.env.ref("base.group_user").id),
                    (
                        4,
                        cls.env.ref(
                            "operating_unit.group_manager_operating_unit"
                        ).id,
                    ),
                ],
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )

        cls.rec_a = cls.Host.create({"name": "rec-a", "operating_unit_id": cls.ou_a.id})
        cls.rec_b = cls.Host.create({"name": "rec-b", "operating_unit_id": cls.ou_b.id})
        cls.rec_c = cls.Host.create({"name": "rec-c", "operating_unit_id": cls.ou_c.id})

    def _schedule(self, host, activity_type):
        return host.activity_schedule(
            activity_type_id=activity_type.id,
            responsible_role_id=self.role.id,
            operating_unit_id=host.operating_unit_id.id,
        )

    def _mine_primary(self):
        return self.Activity.with_user(self.manager).search(
            [("is_my_primary_todo", "=", True)]
        )

    def _mine_oversight(self):
        return self.Activity.with_user(self.manager).search(
            [("is_my_todo", "=", True), ("is_my_primary_todo", "=", False)]
        )

    # ------------------------------------------------------------------
    # Backward compatibility
    # ------------------------------------------------------------------
    def test_default_scope_matches_view_scope(self):
        """Empty notification scope + no rules = every group Todo the manager
        can see lands in primary (the pre-ADR-0007 behaviour)."""
        a = self._schedule(self.rec_a, self.type_a)
        b = self._schedule(self.rec_b, self.type_a)
        c = self._schedule(self.rec_c, self.type_b)
        primary = self._mine_primary()
        self.assertIn(a, primary)
        self.assertIn(b, primary)
        self.assertIn(c, primary)
        self.assertFalse(self._mine_oversight(), "no delta → Oversight is empty")

    # ------------------------------------------------------------------
    # OU-level notification scope
    # ------------------------------------------------------------------
    def test_notify_ou_subset_moves_outsiders_to_oversight(self):
        """Setting notify_operating_unit_ids = [A, B] pushes OU C to Oversight."""
        a = self._schedule(self.rec_a, self.type_a)
        b = self._schedule(self.rec_b, self.type_a)
        c = self._schedule(self.rec_c, self.type_a)
        self.manager.todo_notify_operating_unit_ids = self.ou_a + self.ou_b
        primary = self._mine_primary()
        oversight = self._mine_oversight()
        self.assertIn(a, primary)
        self.assertIn(b, primary)
        self.assertNotIn(c, primary)
        self.assertIn(c, oversight)

    # ------------------------------------------------------------------
    # Per-type rules
    # ------------------------------------------------------------------
    def test_all_ous_rule_widens_a_muted_scope(self):
        """A user with a narrow OU scope still receives an 'all_ous' type from
        every view-scope OU (sarabun confirmations across the org)."""
        a = self._schedule(self.rec_a, self.type_b)  # sarabun in OU A
        c = self._schedule(self.rec_c, self.type_b)  # sarabun in OU C
        self.manager.todo_notify_operating_unit_ids = self.ou_a  # narrow
        self.env["res.users.todo.notify.rule"].create(
            {
                "user_id": self.manager.id,
                "activity_type_id": self.type_b.id,
                "mode": "all_ous",
            }
        )
        primary = self._mine_primary()
        self.assertIn(a, primary)
        self.assertIn(c, primary, "all_ous rule widens sarabun back to every OU")

    def test_mute_rule_drops_type_from_primary(self):
        """A mute rule removes the type from primary regardless of OU."""
        a_plan = self._schedule(self.rec_a, self.type_a)
        a_sarabun = self._schedule(self.rec_a, self.type_b)
        self.env["res.users.todo.notify.rule"].create(
            {
                "user_id": self.manager.id,
                "activity_type_id": self.type_a.id,
                "mode": "mute",
            }
        )
        primary = self._mine_primary()
        oversight = self._mine_oversight()
        self.assertNotIn(a_plan, primary, "muted type drops out of primary")
        self.assertIn(a_plan, oversight, "muted type still visible under Oversight")
        self.assertIn(a_sarabun, primary, "other types unaffected")

    # ------------------------------------------------------------------
    # Personal Todos bypass the filter
    # ------------------------------------------------------------------
    def test_personal_todo_bypasses_scope(self):
        """Personal Todos are explicit routing decisions — the scope filter
        must not silence them (Q6.1)."""
        # Narrow scope AND mute the type — a personal Todo of that type must
        # still hit primary.
        self.manager.todo_notify_operating_unit_ids = self.ou_a  # narrow
        self.env["res.users.todo.notify.rule"].create(
            {
                "user_id": self.manager.id,
                "activity_type_id": self.type_a.id,
                "mode": "mute",
            }
        )
        # Personal Todo in OU C (outside notify scope) of a muted type.
        personal = self.rec_c.activity_schedule(
            activity_type_id=self.type_a.id, user_id=self.manager.id
        )
        primary = self._mine_primary()
        self.assertIn(
            personal,
            primary,
            "personal Todos always enter primary — scope and rules only shape "
            "group Todos",
        )

    # ------------------------------------------------------------------
    # Systray badge follows primary (Q6.2)
    # ------------------------------------------------------------------
    def test_systray_count_uses_primary_domain(self):
        """The badge counts primary Todos only — a manager narrowing scope
        should see a smaller number, not the same total."""
        self._schedule(self.rec_a, self.type_a)
        self._schedule(self.rec_b, self.type_a)
        self._schedule(self.rec_c, self.type_a)
        wide = self.manager.with_user(self.manager).get_my_todo_count()
        self.assertEqual(
            wide["total_count"], 3, "no config → all three count in badge"
        )
        self.manager.todo_notify_operating_unit_ids = self.ou_a  # keep only A
        narrow = self.manager.with_user(self.manager).get_my_todo_count()
        self.assertEqual(
            narrow["total_count"],
            1,
            "narrow scope → badge shrinks to what is actually primary",
        )
