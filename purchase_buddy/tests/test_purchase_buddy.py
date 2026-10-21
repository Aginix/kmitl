from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPurchaseBuddy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        Partner = env["res.partner"]
        cls.parent = Partner.create({"name": "Faculty", "is_company": True})
        cls.child = Partner.create({"name": "Faculty Sub", "parent_id": cls.parent.id})
        cls.other = Partner.create({"name": "Other", "is_company": True})
        groups = "base.group_user,purchase_buddy.group_purchase_buddy"
        cls.buddy_parent = new_test_user(env, login="pb_parent", groups=groups)
        cls.buddy_child = new_test_user(env, login="pb_child", groups=groups)
        cls.Buddy = env["purchase.buddy"]

    def test_group_implies_purchase_request_user(self):
        self.assertTrue(
            self.buddy_parent.has_group("purchase_request.group_purchase_request_user")
        )

    def _row(self, user, domain, model="res.partner", **vals):
        return self.Buddy.create(
            {
                "user_id": user.id,
                "model_id": self.env["ir.model"]._get(model).id,
                "domain": domain,
                **vals,
            }
        )

    def test_child_of_domain_covers_sub_units(self):
        self._row(self.buddy_parent, "[('id', 'child_of', %d)]" % self.parent.id)
        self.assertEqual(self.Buddy._get_buddy_users(self.child), self.buddy_parent)
        self.assertFalse(self.Buddy._get_buddy_users(self.other))

    def test_child_of_domain_matches_unsaved_record(self):
        """A form's onchange works on a new record: child_of must be judged on
        its in-memory value, not by searching the database."""
        self._row(
            self.buddy_parent,
            "[('parent_id', 'child_of', %d)]" % self.parent.id,
        )
        Partner = self.env["res.partner"]
        self.assertEqual(
            self.Buddy._get_buddy_users(Partner.new({"parent_id": self.child.id})),
            self.buddy_parent,
        )
        self.assertFalse(
            self.Buddy._get_buddy_users(Partner.new({"parent_id": self.other.id}))
        )

    def test_sequence_orders_buddies(self):
        self._row(self.buddy_parent, "[('id', 'child_of', %d)]" % self.parent.id)
        self._row(self.buddy_child, "[('id', '=', %d)]" % self.child.id, sequence=1)
        buddies = self.Buddy._get_buddy_users(self.child)
        self.assertEqual(buddies.ids, [self.buddy_child.id, self.buddy_parent.id])
        self.assertEqual(self.Buddy._get_buddy_users(self.parent), self.buddy_parent)

    def test_archived_row_does_not_cover(self):
        self._row(self.buddy_parent, "[]", active=False)
        self.assertFalse(self.Buddy._get_buddy_users(self.parent))

    def test_row_covers_only_its_model(self):
        self._row(self.buddy_parent, "[('state', '=', 'draft')]", "purchase.request")
        PR = self.env["purchase.request"]
        self.assertEqual(
            self.Buddy._get_buddy_users(PR.new({"state": "draft"})),
            self.buddy_parent,
        )
        self.assertFalse(self.Buddy._get_buddy_users(PR.new({"state": "approved"})))
        self.assertFalse(self.Buddy._get_buddy_users(self.parent))

    def test_coverage_shows_names_not_ids(self):
        row = self._row(self.buddy_parent, "[('id', 'child_of', %d)]" % self.parent.id)
        self.assertEqual(row.display_name, self.buddy_parent.display_name)
        self.assertIn("Faculty", row.coverage)
        self.assertNotIn(str(self.parent.id), row.coverage)
        self.assertEqual(self._row(self.buddy_parent, "[]").coverage, "All documents")
        raw = "['|', ('id', '=', %d), ('id', '=', %d)]" % (
            self.parent.id,
            self.other.id,
        )
        self.assertEqual(self._row(self.buddy_parent, raw).coverage, raw)
