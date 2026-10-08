from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.kmitl_project_coordinator.tests.common import (
    KmitlProjectCoordinatorCommon,
)


@tagged("post_install", "-at_install")
class TestSubmitPermission(KmitlProjectCoordinatorCommon):
    """สร้างหนังสือ is reserved to the project's owners and project officers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = cls.env["res.users"].create(
            {
                "name": "kp_officer",
                "login": "kp_officer",
                "groups_id": [
                    Command.set(
                        [cls.env.ref("kmitl_project.group_kmitl_project_user_all").id]
                    )
                ],
            }
        )
        cls.officer.assigned_operating_unit_ids = cls.ou_a
        cls.project.state = "to_send"

    def test_owners_and_officer_may_submit(self):
        for user in (self.creator, self.coordinator, self.manager_user, self.officer):
            project = self.project.with_user(user)
            self.assertTrue(project.can_submit_sarabun, user.login)
            self.assertTrue(project._sarabun_submit_guard(), user.login)

    def test_non_owner_may_not_submit(self):
        # sudo() stands in for a reader who is not an owner (e.g. a Viewer): it
        # passes the record rules but keeps the stranger as the acting user.
        project = self.project.with_user(self.stranger).sudo()
        self.assertFalse(project.can_submit_sarabun)
        with self.assertRaises(AccessError):
            project.action_submit_to_sarabun()
        self.assertFalse(self.project.sarabun_document_ids)
