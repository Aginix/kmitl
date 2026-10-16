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

    def test_parent_coverage_extends_to_children(self):
        self.Buddy.create(
            {"user_id": self.buddy_parent.id, "department_analytic_id": self.parent.id}
        )
        self.assertEqual(self.Buddy._get_buddy_users(self.child), self.buddy_parent)
        self.assertFalse(self.Buddy._get_buddy_users(self.other))

    def test_most_specific_unit_is_primary(self):
        # The parent's buddy ranks first by sequence, yet the sub-unit's own
        # buddy still wins for the sub-unit.
        self.Buddy.create(
            {
                "user_id": self.buddy_parent.id,
                "department_analytic_id": self.parent.id,
                "sequence": 1,
            }
        )
        self.Buddy.create(
            {
                "user_id": self.buddy_child.id,
                "department_analytic_id": self.child.id,
                "sequence": 99,
            }
        )
        buddies = self.Buddy._get_buddy_users(self.child)
        self.assertEqual(buddies.ids, [self.buddy_child.id, self.buddy_parent.id])
        self.assertEqual(self.Buddy._get_buddy_users(self.parent), self.buddy_parent)

    def test_archived_row_does_not_cover(self):
        self.Buddy.create(
            {
                "user_id": self.buddy_parent.id,
                "department_analytic_id": self.parent.id,
                "active": False,
            }
        )
        self.assertFalse(self.Buddy._get_buddy_users(self.parent))

    def test_model_domain_narrows_coverage(self):
        self.Buddy.create(
            {
                "user_id": self.buddy_parent.id,
                "department_analytic_id": self.parent.id,
                "model_id": self.env["ir.model"]._get("budget.move").id,
                "domain": "[('move_type', '=', 'entry')]",
            }
        )
        Move = self.env["budget.move"]
        entry = Move.new(
            {"department_analytic_id": self.child.id, "move_type": "entry"}
        )
        appropriation = Move.new(
            {"department_analytic_id": self.child.id, "move_type": "appropriation"}
        )
        self.assertEqual(
            self.Buddy._get_buddy_users(self.child, entry), self.buddy_parent
        )
        self.assertFalse(self.Buddy._get_buddy_users(self.child, appropriation))
        self.assertFalse(self.Buddy._get_buddy_users(self.child))
