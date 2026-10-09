from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from .common import KmitlProjectCoordinatorCommon


@tagged("post_install", "-at_install")
class TestProjectCoordinator(KmitlProjectCoordinatorCommon):
    """ผู้ประสานงาน is a project owner alongside หัวหน้าโครงการ and the creator:
    Own Project access (incl. child lines), cross-OU visibility, and status
    notifications as an auto-subscribed follower."""

    def _flush_tracking(self):
        self.env.flush_all()
        self.env.cr.precommit.run()

    def test_coordinator_owns_project_across_ou(self):
        project = self.project.with_user(self.coordinator)
        self.assertTrue(project.is_project_owner)
        project.write({"objective": "edited by coordinator"})
        self.env["project.target"].with_user(self.coordinator).create(
            {
                "name": "Students",
                "line_type": "target",
                "project_id": self.project.id,
                "amount": 10,
            }
        )
        self.assertEqual(len(self.project.target_ids), 1)

    def test_manager_reads_project_across_ou(self):
        project = self.project.with_user(self.manager_user)
        self.assertTrue(project.is_project_owner)
        self.assertEqual(project.name, "Coordinated Project")

    def test_non_owner_has_no_access(self):
        self.assertFalse(self.project.with_user(self.stranger).sudo().is_project_owner)
        with self.assertRaises(AccessError):
            self.project.with_user(self.stranger).read(["name"])

    def test_coordinator_follows_and_is_notified_of_status(self):
        partner = self.coordinator.partner_id
        follower = self.project.message_follower_ids.filtered(
            lambda f: f.partner_id == partner
        )
        self.assertIn(self.subtype, follower.subtype_ids)

        self.project.write({"state": "to_verify"})
        self._flush_tracking()
        message = self.project.message_ids.filtered(
            lambda m: m.subtype_id == self.subtype
        )
        self.assertTrue(message)
        self.assertIn(partner, message.notified_partner_ids)

    def test_multiple_coordinators_are_owners_and_followers(self):
        self.project.coordinator_ids = [Command.link(self.stranger.id)]
        self.assertEqual(self.project.coordinator_names, "kp_coordinator, kp_stranger")
        for user in (self.coordinator, self.stranger):
            self.assertTrue(self.project.with_user(user).is_project_owner, user.login)
            follower = self.project.message_follower_ids.filtered(
                lambda f, p=user.partner_id: f.partner_id == p
            )
            self.assertIn(self.subtype, follower.subtype_ids, user.login)

    def test_removed_coordinator_loses_ownership_stays_subscribed(self):
        self.project.coordinator_ids = [Command.set(self.stranger.ids)]
        self.assertFalse(
            self.project.with_user(self.coordinator).sudo().is_project_owner
        )
        # The removed coordinator stays subscribed (Odoo convention).
        self.assertIn(
            self.coordinator.partner_id,
            self.project.message_follower_ids.partner_id,
        )

    def test_existing_follower_gets_status_subtype(self):
        partner = self.manager_user.partner_id
        self.project.message_subscribe(
            partner_ids=partner.ids,
            subtype_ids=self.env.ref("mail.mt_comment").ids,
        )
        self.project.coordinator_ids = [Command.link(self.manager_user.id)]
        follower = self.project.message_follower_ids.filtered(
            lambda f: f.partner_id == partner
        )
        self.assertIn(self.subtype, follower.subtype_ids)
        self.assertIn(self.env.ref("mail.mt_comment"), follower.subtype_ids)
