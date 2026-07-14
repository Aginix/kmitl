from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

ASSIGN_ACTIVITY_XMLID = "base_assignment.mail_activity_assignment"


@tagged("post_install", "-at_install")
class TestKrisProjectAssignment(TransactionCase):
    """Cover the assignment.mixin integration on kris.project.

    Semantics: ``assigned_to`` is the *current handler*, distinct from the
    fixed ``user_id`` ("Responsible"). See kris_project_assignment ADR-0001.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Project = cls.env["kris.project"]
        cls.Wizard = cls.env["assign.officer.wizard"]

        Users = cls.env["res.users"].with_context(no_reset_password=True)
        g_officer = cls.env.ref("kris_project.group_kris_project_officer")
        g_manager = cls.env.ref("kris_project.group_kris_project_manager")
        g_viewer = cls.env.ref("kris_project.group_kris_project_viewer")

        cls.officer_a = Users.create(
            {
                "name": "KRIS Officer A",
                "login": "kris_officer_a",
                "groups_id": [(6, 0, [g_officer.id])],
            }
        )
        cls.officer_b = Users.create(
            {
                "name": "KRIS Officer B",
                "login": "kris_officer_b",
                "groups_id": [(6, 0, [g_officer.id])],
            }
        )
        cls.manager = Users.create(
            {
                "name": "KRIS Manager",
                "login": "kris_manager",
                "groups_id": [(6, 0, [g_manager.id])],
            }
        )
        cls.viewer = Users.create(
            {
                "name": "KRIS Viewer",
                "login": "kris_viewer",
                "groups_id": [(6, 0, [g_viewer.id])],
            }
        )

        cls.category = cls.env["kris.project.category"].create(
            {"name": "Assignment Test Category"}
        )
        cls.ptype = cls.env["kris.project.type"].create(
            {"name": "Assignment Test Type", "category_id": cls.category.id}
        )

    def _make_project(self):
        return self.Project.create(
            {
                "project_name": "Assignment Test Project",
                "project_category_id": self.category.id,
                "project_type_id": self.ptype.id,
            }
        )

    def _assignment_activities(self, project, user=None):
        activity_type = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        acts = project.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type
        )
        if user is not None:
            acts = acts.filtered(lambda a: a.user_id == user)
        return acts

    # ------------------------------------------------------------------
    # Claim
    # ------------------------------------------------------------------
    def test_officer_can_claim_unassigned(self):
        project = self._make_project()
        project.with_user(self.officer_a).action_assignment_assign_me()
        self.assertEqual(project.assigned_to, self.officer_a)
        self.assertEqual(len(self._assignment_activities(project, self.officer_a)), 1)

    def test_officer_cannot_claim_already_assigned(self):
        project = self._make_project()
        project.with_user(self.officer_a).action_assignment_assign_me()
        with self.assertRaises(UserError):
            project.with_user(self.officer_b).action_assignment_assign_me()
        # Officer A still holds the record.
        self.assertEqual(project.assigned_to, self.officer_a)

    # ------------------------------------------------------------------
    # Manager reassign via wizard
    # ------------------------------------------------------------------
    def test_manager_can_reassign_via_wizard(self):
        project = self._make_project()
        project.with_user(self.officer_a).action_assignment_assign_me()
        self.assertEqual(len(self._assignment_activities(project, self.officer_a)), 1)
        wiz = self.Wizard.with_user(self.manager).create(
            {
                "res_model": "kris.project",
                "res_id": project.id,
                "user_id": self.officer_b.id,
            }
        )
        wiz.action_assign()
        self.assertEqual(project.assigned_to, self.officer_b)
        self.assertFalse(self._assignment_activities(project, self.officer_a))
        self.assertEqual(len(self._assignment_activities(project, self.officer_b)), 1)

    def test_non_manager_cannot_open_wizard(self):
        project = self._make_project()
        with self.assertRaises(AccessError):
            project.with_user(self.officer_a).action_assignment_open_wizard()

    # ------------------------------------------------------------------
    # Unassign
    # ------------------------------------------------------------------
    def test_manager_can_unassign(self):
        project = self._make_project()
        project.with_user(self.officer_a).action_assignment_assign_me()
        project.with_user(self.manager).action_assignment_unassign()
        self.assertFalse(project.assigned_to)
        self.assertFalse(self._assignment_activities(project))

    def test_non_manager_cannot_unassign(self):
        project = self._make_project()
        project.with_user(self.officer_a).action_assignment_assign_me()
        with self.assertRaises(AccessError):
            project.with_user(self.officer_b).action_assignment_unassign()

    # ------------------------------------------------------------------
    # Auto-clear on close state
    # ------------------------------------------------------------------
    def test_activity_cleared_on_close_state(self):
        for state in ("done", "cancel", "terminated", "conditional_close"):
            with self.subTest(state=state):
                project = self._make_project()
                project.with_user(self.officer_a).action_assignment_assign_me()
                self.assertEqual(
                    len(self._assignment_activities(project, self.officer_a)),
                    1,
                )
                project.write({"state": state})
                # Assignment field is preserved as history; only the open
                # To-Do is cleared.
                self.assertEqual(project.assigned_to, self.officer_a)
                self.assertFalse(self._assignment_activities(project))

    # ------------------------------------------------------------------
    # Banner injection smoke-test
    # ------------------------------------------------------------------
    def test_banner_injected_in_form_view(self):
        view = self.Project.get_view(view_type="form")
        arch = view["arch"]
        if isinstance(arch, (bytes, bytearray)):
            arch = arch.decode("utf-8")
        # Sanity: three telltale strings from base_assignment's banner
        # template survive the get_view rewrite.
        self.assertIn("action_assignment_assign_me", arch)
        self.assertIn("action_assignment_open_wizard", arch)
        self.assertIn("action_assignment_unassign", arch)

    # ------------------------------------------------------------------
    # Copy safety
    # ------------------------------------------------------------------
    def test_copy_does_not_carry_assignment(self):
        project = self._make_project()
        project.with_user(self.officer_a).action_assignment_assign_me()
        clone = project.copy()
        self.assertFalse(clone.assigned_to)
