from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestBudgetBuddy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        Plan = env["account.analytic.plan"]
        plan = Plan.search([("code", "=", "departments")], limit=1) or Plan.create(
            {"name": "Departments", "code": "departments"}
        )
        AA = env["account.analytic.account"]
        cls.parent = AA.create({"name": "Faculty", "code": "BB_P", "plan_id": plan.id})
        cls.child = AA.create(
            {
                "name": "Faculty Sub",
                "code": "BB_C",
                "plan_id": plan.id,
                "parent_id": cls.parent.id,
            }
        )
        cls.other = AA.create({"name": "Other", "code": "BB_O", "plan_id": plan.id})
        groups = "base.group_user,budget_buddy.group_budget_buddy"
        cls.buddy_parent = new_test_user(env, login="bb_parent", groups=groups)
        cls.buddy_child = new_test_user(env, login="bb_child", groups=groups)
        cls.Buddy = env["budget.buddy"]

    def test_group_implies_budget_user(self):
        self.assertTrue(self.buddy_parent.has_group("budget.group_budget_user"))

    def _row(self, user, domain, model="account.analytic.account", **vals):
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
        AA = self.env["account.analytic.account"]
        self.assertEqual(
            self.Buddy._get_buddy_users(AA.new({"parent_id": self.child.id})),
            self.buddy_parent,
        )
        self.assertFalse(
            self.Buddy._get_buddy_users(AA.new({"parent_id": self.other.id}))
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
        self._row(self.buddy_parent, "[('move_type', '=', 'entry')]", "budget.move")
        Move = self.env["budget.move"]
        entry = Move.new({"move_type": "entry"})
        appropriation = Move.new({"move_type": "appropriation"})
        self.assertEqual(self.Buddy._get_buddy_users(entry), self.buddy_parent)
        self.assertFalse(self.Buddy._get_buddy_users(appropriation))
        self.assertFalse(self.Buddy._get_buddy_users(self.parent))
