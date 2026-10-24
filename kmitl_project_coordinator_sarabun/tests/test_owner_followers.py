from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.kmitl_project_coordinator.tests.common import (
    KmitlProjectCoordinatorCommon,
)


@tagged("post_install", "-at_install")
class TestOwnerFollowers(KmitlProjectCoordinatorCommon):
    """The project's owners follow its หนังสือ, so they may read it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project.state = "to_send"
        action = cls.project.with_user(cls.creator).action_submit_to_sarabun()
        cls.document = cls.env["sarabun.document"].browse(action["res_id"])

    def test_owners_follow_and_read(self):
        owners = self.creator | self.coordinator | self.manager_user
        self.assertLessEqual(owners.partner_id, self.document.message_partner_ids)
        for user in owners:
            self.assertTrue(self.document.with_user(user).subject, user.login)
        self.assertNotIn(self.stranger.partner_id, self.document.message_partner_ids)

    def test_owner_change_syncs_followers(self):
        self.project.coordinator_ids = [Command.set(self.stranger.ids)]
        self.assertIn(self.stranger.partner_id, self.document.message_partner_ids)
        self.assertNotIn(self.coordinator.partner_id, self.document.message_partner_ids)
