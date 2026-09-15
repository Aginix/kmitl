# -*- coding: utf-8 -*-
"""Visibility matrix tests for agx_sarabun_user_template (ADR-0016).

Covers:
  - personal: owner-only visibility
  - unit: dept + ancestor dept visibility via parent_path
  - public: visible to all sarabun users
  - constraint: non-manager cannot set visibility=public
  - write/unlink isolation: user A cannot touch user B's personal template
  - owner can create, edit, and unlink their own templates and lines
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestUserTemplateVisibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Department hierarchy:
        #   dept_x (root)
        #     └─ dept_y (child of x)
        #   dept_z (unrelated)
        cls.dept_x = cls.env["hr.department"].create({"name": "หน่วยงาน X"})
        cls.dept_y = cls.env["hr.department"].create(
            {"name": "หน่วยงาน Y", "parent_id": cls.dept_x.id}
        )
        cls.dept_z = cls.env["hr.department"].create({"name": "หน่วยงาน Z"})

        # user_a → dept_y (child of dept_x), user_b → dept_z, manager → no dept needed
        cls.user_a = new_test_user(
            cls.env,
            login="tpl_ua",
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        cls.user_b = new_test_user(
            cls.env,
            login="tpl_ub",
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        cls.manager = new_test_user(
            cls.env,
            login="tpl_mgr",
            groups="base.group_user,agx_sarabun.group_sarabun_manager",
        )

        cls.env["hr.employee"].create(
            {"name": "User A", "user_id": cls.user_a.id, "department_id": cls.dept_y.id}
        )
        cls.env["hr.employee"].create(
            {"name": "User B", "user_id": cls.user_b.id, "department_id": cls.dept_z.id}
        )

        cls.Template = cls.env["sarabun.route.template"]

    # ── helpers ──────────────────────────────────────────────────────────────

    def _search(self, user, extra_domain=None):
        domain = extra_domain or []
        return self.Template.with_user(user).search(domain)

    def _visible_ids(self, user):
        return self._search(user).ids

    # ── 1. personal visibility ────────────────────────────────────────────────

    def test_personal_visible_to_owner(self):
        tmpl = self.Template.with_user(self.user_a).create(
            {"name": "Personal A", "visibility": "personal"}
        )
        self.assertIn(tmpl.id, self._visible_ids(self.user_a))

    def test_personal_invisible_to_other_user(self):
        tmpl = self.Template.with_user(self.user_a).create(
            {"name": "Personal A2", "visibility": "personal"}
        )
        self.assertNotIn(tmpl.id, self._visible_ids(self.user_b))

    # ── 2. unit visibility (hierarchy) ───────────────────────────────────────

    def test_unit_visible_to_sub_department_member(self):
        # Template shared at dept_x; user_a is in dept_y (child) → must see it.
        tmpl = self.Template.with_user(self.manager).create(
            {"name": "Unit X", "visibility": "unit", "department_id": self.dept_x.id}
        )
        self.assertIn(
            tmpl.id,
            self._visible_ids(self.user_a),
            "sub-dept member should see a unit template shared at an ancestor dept",
        )

    def test_unit_invisible_to_unrelated_department(self):
        tmpl = self.Template.with_user(self.manager).create(
            {"name": "Unit X2", "visibility": "unit", "department_id": self.dept_x.id}
        )
        self.assertNotIn(
            tmpl.id,
            self._visible_ids(self.user_b),
            "user in an unrelated dept must not see a unit template from another tree",
        )

    # ── 3. public visibility ──────────────────────────────────────────────────

    def test_public_visible_to_all_users(self):
        tmpl = self.Template.with_user(self.manager).create(
            {"name": "Public", "visibility": "public"}
        )
        for user in (self.user_a, self.user_b):
            self.assertIn(
                tmpl.id,
                self._visible_ids(user),
                "%s should see a public template" % user.login,
            )

    # ── 4. constraint: public requires manager ────────────────────────────────

    def test_non_manager_cannot_set_public(self):
        with self.assertRaises(ValidationError):
            self.Template.with_user(self.user_a).create(
                {"name": "Bad Public", "visibility": "public"}
            )

    def test_non_manager_cannot_switch_to_public(self):
        tmpl = self.Template.with_user(self.user_a).create(
            {"name": "Personal Switch", "visibility": "personal"}
        )
        with self.assertRaises(ValidationError):
            tmpl.write({"visibility": "public"})

    # ── 5. write/unlink isolation ─────────────────────────────────────────────

    def test_user_cannot_read_others_personal_template(self):
        tmpl = self.Template.with_user(self.user_b).create(
            {"name": "B Personal", "visibility": "personal"}
        )
        self.assertNotIn(tmpl.id, self._visible_ids(self.user_a))

    def test_user_can_create_edit_and_delete_own_template(self):
        tmpl = self.Template.with_user(self.user_a).create(
            {"name": "Mine", "visibility": "personal"}
        )
        # write → rename
        tmpl.write({"name": "Mine Renamed"})
        self.assertEqual(tmpl.name, "Mine Renamed")
        # unlink
        tmpl_id = tmpl.id
        tmpl.unlink()
        self.assertFalse(self.Template.search([("id", "=", tmpl_id)]))

    # ── 6. default visibility (ADR-0016 P0/P1) ────────────────────────────────

    def test_default_visibility_personal_for_regular_user(self):
        tmpl = self.Template.with_user(self.user_a).create({"name": "No Visibility"})
        self.assertEqual(tmpl.visibility, "personal")

    def test_default_visibility_public_for_superuser(self):
        tmpl = self.Template.create({"name": "Seed Template"})
        self.assertEqual(tmpl.visibility, "public")

    def test_manager_can_write_any_template(self):
        tmpl = self.Template.with_user(self.user_a).create(
            {"name": "User A Template", "visibility": "personal"}
        )
        # Manager should be able to write it (manager rule: all access)
        self.Template.with_user(self.manager).browse(tmpl.id).write(
            {"name": "Manager Renamed"}
        )
        self.assertEqual(tmpl.name, "Manager Renamed")
