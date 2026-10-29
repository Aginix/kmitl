from odoo.tests.common import new_test_user, tagged

from odoo.addons.kmitl_project.tests import test_project_lifecycle as lifecycle_tests


@tagged("post_install", "-at_install")
class TestKmitlProjectChangeRequest(lifecycle_tests.TestProjectLifecycle):
    """Whoever checks a project details what to fix as Change requests
    (reuses the project lifecycle fixtures)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = new_test_user(
            cls.env,
            login="cr_owner",
            groups="base.group_user,kmitl_project.group_kmitl_project_user",
        )
        cls.outsider = new_test_user(
            cls.env,
            login="cr_outsider",
            groups="base.group_user,kmitl_project.group_kmitl_project_user",
        )
        cls.officer = new_test_user(
            cls.env,
            login="cr_officer",
            groups="base.group_user,kmitl_project.group_kmitl_project_user_all",
        )

    def _to_verify(self):
        project = self._make_project(
            creating_user_id=self.owner.id, operating_unit_id=False
        )
        project.action_confirm()
        return project

    def _ask(self, project, user, assignees=()):
        return (
            self.env["change.request"]
            .with_user(user)
            .request_create(
                project._name, project.id, "แผนงบประมาณไม่ตรงกับกิจกรรม", list(assignees)
            )
        )

    def test_request_notifies_without_blocking(self):
        project = self._to_verify()
        self._ask(project, self.officer, [self.owner.id])
        self.assertEqual(project.change_request_count, 1)
        self.assertTrue(
            project.activity_ids.filtered(lambda a: a.user_id == self.owner)
        )
        # Outstanding requests never hold up ยืนยันงบประมาณ.
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        self.assertEqual(project.state, "to_send")

    def test_officer_closes_on_behalf(self):
        project = self._to_verify()
        request = self._ask(project, self.owner)
        Request = self.env["change.request"]
        with self.assertRaises(Exception):
            Request.with_user(self.outsider).request_set_closed(request["id"], True)
        closed = Request.with_user(self.officer).request_set_closed(request["id"], True)
        self.assertEqual(closed["state"], "closed")


# Run only the tests above, not the inherited lifecycle ones again (the base
# class is reached through its module for the same reason).
for _name in dir(lifecycle_tests.TestProjectLifecycle):
    if _name.startswith("test_") and _name not in vars(TestKmitlProjectChangeRequest):
        setattr(TestKmitlProjectChangeRequest, _name, None)
