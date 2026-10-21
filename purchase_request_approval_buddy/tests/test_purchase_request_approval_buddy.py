from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestApprovalBuddy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        Plan = env["account.analytic.plan"]
        plan = Plan.search([("code", "=", "departments")], limit=1) or Plan.create(
            {"name": "Departments", "code": "departments"}
        )
        AA = env["account.analytic.account"]
        cls.faculty = AA.create(
            {"name": "Faculty", "code": "PRAB_F", "plan_id": plan.id}
        )
        cls.sub_unit = AA.create(
            {
                "name": "Faculty Sub",
                "code": "PRAB_S",
                "plan_id": plan.id,
                "parent_id": cls.faculty.id,
            }
        )
        cls.other = AA.create({"name": "Other", "code": "PRAB_O", "plan_id": plan.id})
        groups = "base.group_user,purchase_buddy.group_purchase_buddy"
        cls.buddy_a = new_test_user(env, login="prab_a", groups=groups)
        cls.buddy_b = new_test_user(env, login="prab_b", groups=groups)
        cls.buddy_other = new_test_user(env, login="prab_o", groups=groups)
        model = env["ir.model"]._get("purchase.request.approval")
        Buddy = env["purchase.buddy"]
        for user, unit, sequence in (
            (cls.buddy_a, cls.faculty, 1),
            (cls.buddy_b, cls.faculty, 2),
            (cls.buddy_other, cls.other, 1),
        ):
            Buddy.create(
                {
                    "user_id": user.id,
                    "model_id": model.id,
                    "domain": "[('requesting_department_id', 'child_of', %d)]"
                    % unit.id,
                    "sequence": sequence,
                }
            )

    def _make_pr(self, unit):
        return self.env["purchase.request"].create(
            {
                "title": "Test PR",
                "requested_by": self.env.ref("base.user_admin").id,
                "requesting_department_id": unit.id if unit else False,
            }
        )

    def _make_pa(self, unit):
        return self.env["purchase.request.approval"].create(
            self._make_pr(unit)._prepare_approval_vals()
        )

    def test_default_is_first_covering_buddy(self):
        """A sub-unit is covered by the faculty's rows; sequence picks A."""
        self.assertEqual(self._make_pa(self.sub_unit).assigned_to, self.buddy_a)

    def test_prepare_vals_leaves_officer_to_compute(self):
        vals = self._make_pr(self.faculty)._prepare_approval_vals()
        self.assertNotIn("assigned_to", vals)

    def test_manual_pick_kept_while_still_covering(self):
        pa = self._make_pa(self.faculty)
        pa.assigned_to = self.buddy_b
        pa.requesting_department_id = self.sub_unit
        self.assertEqual(pa.assigned_to, self.buddy_b)

    def test_officer_replaced_when_no_longer_covering(self):
        pa = self._make_pa(self.faculty)
        pa.requesting_department_id = self.other
        self.assertEqual(pa.assigned_to, self.buddy_other)

    def test_no_matching_row_leaves_officer_empty(self):
        self.assertFalse(self._make_pa(False).assigned_to)

    def test_any_buddy_may_be_picked(self):
        """Coverage only sets the default: a Buddy covering another unit may
        stand in."""
        pa = self._make_pa(self.faculty)
        pa.assigned_to = self.buddy_other
        self.assertEqual(pa.assigned_to, self.buddy_other)

    def test_officer_frozen_once_submitted(self):
        pa = self._make_pa(self.faculty)
        pa.state = "to_approve"
        pa.requesting_department_id = self.other
        self.assertEqual(pa.assigned_to, self.buddy_a)
