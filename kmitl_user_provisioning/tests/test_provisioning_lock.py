# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProvisioningLock(TransactionCase):
    """_is_provisioning_locked() gates exactly the un-provisioned internal users."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Users = cls.env["res.users"].with_context(no_reset_password=True)
        # A functional group that a plain new user never gets by default.
        cls.functional_group = cls.env["res.groups"].create(
            {"name": "Test Functional Group"}
        )

    def _new_internal_user(self, login):
        # No groups_id passed -> Odoo applies base.default_user groups, i.e. a
        # plain internal user, exactly like a freshly created account.
        return self.Users.create({"name": login, "login": login})

    def test_locked_plain_internal_user_without_employee(self):
        user = self._new_internal_user("locked_user")
        self.assertTrue(user._is_provisioning_locked())

    def test_not_locked_when_employee_linked(self):
        user = self._new_internal_user("employee_user")
        self.env["hr.employee"].create({"name": "Emp", "user_id": user.id})
        self.assertFalse(user._is_provisioning_locked())

    def test_not_locked_with_functional_group(self):
        user = self._new_internal_user("granted_user")
        user.groups_id = [(4, self.functional_group.id)]
        self.assertFalse(user._is_provisioning_locked())

    def test_not_locked_for_admin(self):
        admin = self._new_internal_user("admin_user")
        admin.groups_id = [(4, self.env.ref("base.group_system").id)]
        self.assertFalse(admin._is_provisioning_locked())

    def test_not_locked_for_superuser(self):
        self.assertFalse(
            self.env["res.users"].browse(SUPERUSER_ID)._is_provisioning_locked()
        )

    def test_not_locked_for_portal_user(self):
        portal = self.Users.create(
            {
                "name": "portal_user",
                "login": "portal_user",
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        self.assertFalse(portal._is_provisioning_locked())
