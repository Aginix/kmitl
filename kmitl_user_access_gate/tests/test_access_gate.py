from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestUserAccessGate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Users = cls.env["res.users"]
        cls.internal_group = cls.env.ref("base.group_user")
        cls.portal_group = cls.env.ref("base.group_portal")

    def _create_user(self, login, group):
        return self.Users.create(
            {
                "name": login,
                "login": login,
                "groups_id": [(6, 0, group.ids)],
            }
        )

    def test_internal_user_without_employee_is_stripped(self):
        user = self._create_user("gate_internal", self.internal_group)
        self.assertTrue(user.groups_id)
        user._update_last_login()
        self.assertFalse(user.groups_id, "Groups should be cleared")

    def test_user_with_employee_keeps_access(self):
        user = self._create_user("gate_with_emp", self.internal_group)
        self.env["hr.employee"].create({"name": "Emp", "user_id": user.id})
        before = user.groups_id
        user._update_last_login()
        self.assertEqual(user.groups_id, before, "Groups should be preserved")

    def test_admin_without_employee_keeps_access(self):
        admin = self.env.ref("base.user_admin")
        admin.employee_ids.unlink()
        before = admin.groups_id
        admin._update_last_login()
        self.assertEqual(admin.groups_id, before, "Admin must stay exempt")

    def test_portal_user_without_employee_keeps_access(self):
        user = self._create_user("gate_portal", self.portal_group)
        before = user.groups_id
        user._update_last_login()
        self.assertEqual(
            user.groups_id, before, "Portal users must not be stripped"
        )
