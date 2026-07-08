# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.disbursement_request_assignment import (
    ASSIGN_ACTIVITY_XMLID,
    TAKEOVER_PARAM,
)


@tagged("post_install", "-at_install")
class TestDisbursementAssignment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DR = cls.env["disbursement.request"]
        cls.Rule = cls.env["disbursement.assignment.rule"]
        cls.Wizard = cls.env["disbursement.assign.officer.wizard"]

        # -- analytic dimensions ----------------------------------------
        AAA = cls.env["account.analytic.account"]
        dep_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_departments")
        src_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_sources")
        fund_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_funds")
        act_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_activities")

        cls.dept_parent = AAA.create(
            {"name": "Faculty", "plan_id": dep_plan.id}
        )
        cls.dept_child = AAA.create(
            {
                "name": "Department",
                "plan_id": dep_plan.id,
                "parent_id": cls.dept_parent.id,
            }
        )
        cls.source_gov = AAA.create(
            {"name": "Government Budget", "plan_id": src_plan.id}
        )
        cls.source_rev = AAA.create(
            {"name": "Revenue Budget", "plan_id": src_plan.id}
        )
        cls.fund_a = AAA.create({"name": "General Fund", "plan_id": fund_plan.id})
        cls.activity_a = AAA.create(
            {"name": "Education Support", "plan_id": act_plan.id}
        )

        # -- partner types & partners -----------------------------------
        PType = cls.env["res.partner.type"]
        cls.pt_a = PType.create({"name": "Type A", "company_type": "company"})
        cls.pt_b = PType.create({"name": "Type B", "company_type": "company"})
        Partner = cls.env["res.partner"]
        cls.partner_a = Partner.create(
            {"name": "Partner A", "partner_type_id": cls.pt_a.id}
        )
        cls.partner_b = Partner.create(
            {"name": "Partner B", "partner_type_id": cls.pt_b.id}
        )

        cls.product = cls.env["product.product"].create(
            {"name": "Test Service", "type": "service"}
        )

        # -- users -------------------------------------------------------
        users = cls.env["res.users"].with_context(no_reset_password=True)
        g_officer = cls.env.ref("disbursement.group_disbursement_officer")
        g_manager = cls.env.ref("disbursement.group_disbursement_manager")
        g_user = cls.env.ref("base.group_user")
        cls.officer_a = users.create(
            {
                "name": "Officer A",
                "login": "dr_officer_a",
                "groups_id": [(6, 0, [g_officer.id])],
            }
        )
        cls.officer_b = users.create(
            {
                "name": "Officer B",
                "login": "dr_officer_b",
                "groups_id": [(6, 0, [g_officer.id])],
            }
        )
        cls.manager = users.create(
            {
                "name": "DR Manager",
                "login": "dr_manager",
                "groups_id": [(6, 0, [g_manager.id])],
            }
        )
        cls.outsider = users.create(
            {
                "name": "Outsider",
                "login": "dr_outsider",
                "groups_id": [(6, 0, [g_user.id])],
            }
        )

    # -- helpers ---------------------------------------------------------
    def _make_dr(
        self,
        source=None,
        department=None,
        partner=None,
        partners=None,
        sign=True,
        sign_as=None,
    ):
        source = source or self.source_gov
        department = department or self.dept_child
        partners = partners or [partner or self.partner_a]
        vals = {
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product.id,
                        "name": "Test line",
                        "quantity": 1.0,
                        "price_unit": 100.0,
                        "partner_id": p.id,
                    },
                )
                for p in partners
            ]
        }
        dr = self.DR.create(vals)
        dr.analytic_distribution = {
            str(department.id): 100,
            str(source.id): 100,
            str(self.fund_a.id): 100,
            str(self.activity_a.id): 100,
        }
        dr.action_submit()
        if sign:
            dr.with_user(sign_as or self.manager).action_sign()
        return dr

    def _todos(self, record, user):
        todo = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        summary = record._assignment_activity_summary()
        return record.activity_ids.filtered(
            lambda a: a.user_id == user
            and a.activity_type_id == todo
            and a.summary == summary
        )

    def _reassign(self, request, user):
        self.Wizard.with_user(self.manager).create(
            {"request_id": request.id, "user_id": user.id}
        ).action_assign()

    # -- matching --------------------------------------------------------
    def test_exact_match_raises_todo(self):
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_child.id,
                "source_analytic_id": self.source_gov.id,
                "fund_analytic_id": self.fund_a.id,
                "activity_analytic_id": self.activity_a.id,
                "partner_type_id": self.pt_a.id,
            }
        )
        dr = self._make_dr(partner=self.partner_a)
        self.assertEqual(dr.assigned_to, self.officer_a)
        self.assertTrue(self._todos(dr, self.officer_a))

    def test_wildcard_rule_matches(self):
        self.Rule.create({"user_id": self.officer_a.id})
        dr = self._make_dr()
        self.assertEqual(dr.assigned_to, self.officer_a)

    def test_and_of_multiple_criteria(self):
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_child.id,
                "source_analytic_id": self.source_gov.id,
            }
        )
        matched = self._make_dr(department=self.dept_child, source=self.source_gov)
        self.assertEqual(matched.assigned_to, self.officer_a)
        missed = self._make_dr(department=self.dept_child, source=self.source_rev)
        self.assertFalse(missed.assigned_to)

    def test_parent_rule_covers_child(self):
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_parent.id,
            }
        )
        dr = self._make_dr(department=self.dept_child)
        self.assertEqual(dr.assigned_to, self.officer_a)

    def test_child_rule_does_not_cover_parent(self):
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_child.id,
            }
        )
        dr = self._make_dr(department=self.dept_parent)
        self.assertFalse(dr.assigned_to)

    def test_sequence_decides_first_match(self):
        self.Rule.create({"user_id": self.officer_a.id, "sequence": 5})
        self.Rule.create({"user_id": self.officer_b.id, "sequence": 1})
        dr = self._make_dr()
        self.assertEqual(dr.assigned_to, self.officer_b)

    def test_partner_type_match_and_mismatch(self):
        self.Rule.create(
            {"user_id": self.officer_a.id, "partner_type_id": self.pt_a.id}
        )
        self.Rule.create({"user_id": self.officer_b.id})
        dr_a = self._make_dr(partner=self.partner_a)
        self.assertEqual(dr_a.assigned_to, self.officer_a)
        dr_b = self._make_dr(partner=self.partner_b)
        self.assertEqual(dr_b.assigned_to, self.officer_b)

    def test_mixed_partner_types_match_only_agnostic_rule(self):
        self.Rule.create(
            {"user_id": self.officer_a.id, "partner_type_id": self.pt_a.id}
        )
        self.Rule.create({"user_id": self.officer_b.id})
        # Lines with different partner types -> no single partner type to key
        # on, so only the partner-type-agnostic (wildcard) rule matches.
        dr = self._make_dr(partners=[self.partner_a, self.partner_b])
        self.assertEqual(dr.assigned_to, self.officer_b)

    def test_no_rule_leaves_unassigned(self):
        dr = self._make_dr()
        self.assertFalse(dr.assigned_to)

    def test_inactive_rule_skipped(self):
        self.Rule.create({"user_id": self.officer_a.id, "active": False})
        dr = self._make_dr()
        self.assertFalse(dr.assigned_to)

    def test_archived_officer_skipped(self):
        self.officer_a.active = False
        self.Rule.create({"user_id": self.officer_a.id})
        dr = self._make_dr()
        self.assertFalse(dr.assigned_to)

    # -- notify / self-sign ---------------------------------------------
    def test_self_sign_creates_no_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        dr = self._make_dr(sign_as=self.officer_a)
        self.assertEqual(dr.assigned_to, self.officer_a)
        self.assertFalse(self._todos(dr, self.officer_a))

    # -- manual override / re-sign --------------------------------------
    def test_manual_assign_not_overwritten_and_resign_keeps_officer(self):
        self.Rule.create({"user_id": self.officer_a.id})
        dr = self._make_dr()
        self.assertEqual(dr.assigned_to, self.officer_a)
        # Manager reassigns to B.
        self._reassign(dr, self.officer_b)
        self.assertEqual(dr.assigned_to, self.officer_b)
        self.assertFalse(self._todos(dr, self.officer_a))
        self.assertEqual(len(self._todos(dr, self.officer_b)), 1)
        # Reset to draft closes the to-do but keeps the officer.
        dr.action_draft()
        self.assertFalse(self._todos(dr, self.officer_b))
        self.assertEqual(dr.assigned_to, self.officer_b)
        # Re-sign keeps B (rule points to A) and notifies exactly once.
        dr.action_submit()
        dr.with_user(self.manager).action_sign()
        self.assertEqual(dr.assigned_to, self.officer_b)
        self.assertEqual(len(self._todos(dr, self.officer_b)), 1)

    # -- validate closes the to-do (not locked) -------------------------
    def test_validate_by_other_officer_closes_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        dr = self._make_dr()
        self.assertTrue(self._todos(dr, self.officer_a))
        dr.with_user(self.officer_b).action_validate()
        self.assertEqual(dr.state, "verified")
        self.assertFalse(self._todos(dr, self.officer_a))

    # -- takeover guard --------------------------------------------------
    def test_takeover_default_true_allows_claim(self):
        dr = self._make_dr()
        dr.assigned_to = self.officer_a
        dr.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(dr.assigned_to, self.officer_b)

    def test_takeover_disabled_blocks_claim(self):
        self.env["ir.config_parameter"].sudo().set_param(TAKEOVER_PARAM, "False")
        dr = self._make_dr()
        dr.assigned_to = self.officer_a
        with self.assertRaises(UserError):
            dr.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(dr.assigned_to, self.officer_a)

    def test_can_claim_logic(self):
        dr = self._make_dr()
        self.assertTrue(dr.with_user(self.officer_a).assignment_can_assign_me)
        dr.assigned_to = self.officer_a
        self.assertFalse(dr.with_user(self.officer_a)._assignment_can_claim())
        # takeover default True -> another officer may still claim
        self.assertTrue(dr.with_user(self.officer_b)._assignment_can_claim())
        self.env["ir.config_parameter"].sudo().set_param(TAKEOVER_PARAM, "False")
        self.assertFalse(dr.with_user(self.officer_b)._assignment_can_claim())

    # -- manager-only actions -------------------------------------------
    def test_manager_unassign_clears_field_and_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        dr = self._make_dr()
        dr.with_user(self.manager).action_assignment_unassign()
        self.assertFalse(dr.assigned_to)
        self.assertFalse(self._todos(dr, self.officer_a))

    def test_user_cannot_unassign(self):
        dr = self._make_dr()
        dr.assigned_to = self.officer_a
        with self.assertRaises(AccessError):
            dr.with_user(self.officer_a).action_assignment_unassign()

    def test_user_cannot_open_wizard(self):
        dr = self._make_dr()
        with self.assertRaises(AccessError):
            dr.with_user(self.officer_a).action_assignment_open_wizard()

    # -- wizard ----------------------------------------------------------
    def test_wizard_allowed_users_are_officer_group(self):
        dr = self._make_dr()
        wiz = self.Wizard.with_user(self.manager).create(
            {"request_id": dr.id, "user_id": self.officer_a.id}
        )
        self.assertIn(self.officer_a, wiz.allowed_user_ids)
        self.assertNotIn(self.outsider, wiz.allowed_user_ids)

    # -- re-apply to backlog --------------------------------------------
    def test_apply_to_pending_assigns_only_empty(self):
        empty = self._make_dr()
        self.assertFalse(empty.assigned_to)
        taken = self._make_dr()
        taken.assigned_to = self.officer_b
        self.Rule.create({"user_id": self.officer_a.id})
        self.Rule.action_apply_to_pending()
        self.assertEqual(empty.assigned_to, self.officer_a)
        self.assertEqual(taken.assigned_to, self.officer_b)

    def test_apply_to_pending_ignores_archived_rule(self):
        dr = self._make_dr()
        self.assertFalse(dr.assigned_to)
        rule = self.Rule.create({"user_id": self.officer_a.id})
        rule.active = False
        # The gear-menu action leaks active_test=False into the server action;
        # matching must still skip archived rules.
        self.Rule.with_context(active_test=False).action_apply_to_pending()
        self.assertFalse(dr.assigned_to)
