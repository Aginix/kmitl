# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.assignment import TAKEOVER_PARAM


@tagged("post_install", "-at_install")
class TestPurchaseRequestApprovalAssignment(TransactionCase):
    """PA carries its own Assigned Officer, independent of PR — see ADR-0006."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PR = cls.env["purchase.request"]
        cls.PA = cls.env["purchase.request.approval"]
        cls.Wizard = cls.env["assign.officer.wizard"]

        users = cls.env["res.users"].with_context(no_reset_password=True)
        g_pr_user_all = cls.env.ref(
            "purchase_request_kmitl.group_purchase_request_user_all"
        )
        g_pr_manager = cls.env.ref(
            "purchase_request.group_purchase_request_manager"
        )

        cls.officer_a = users.create(
            {
                "name": "PA Officer A",
                "login": "pa_pa_officer_a",
                "groups_id": [(6, 0, [g_pr_user_all.id])],
            }
        )
        cls.officer_b = users.create(
            {
                "name": "PA Officer B",
                "login": "pa_pa_officer_b",
                "groups_id": [(6, 0, [g_pr_user_all.id])],
            }
        )
        cls.manager = users.create(
            {
                "name": "PA Approval Manager",
                "login": "pa_pa_manager",
                "groups_id": [(6, 0, [g_pr_manager.id])],
            }
        )

        picking_type = cls.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        cls.pr = cls.PR.create({"picking_type_id": picking_type.id})
        cls.pa = cls.PA.create({"request_id": cls.pr.id})

    def _todo_activities(self, record, user):
        todo = self.env.ref("mail.mail_activity_data_todo")
        summary = record._assignment_activity_summary()
        return record.activity_ids.filtered(
            lambda a: a.user_id == user
            and a.activity_type_id == todo
            and a.summary == summary
        )

    # -- independence from PR ---------------------------------------------
    def test_new_pa_starts_unassigned_even_if_pr_is_assigned(self):
        self.pr.assigned_to = self.officer_a
        pa = self.PA.create({"request_id": self.pr.id})
        self.assertFalse(pa.pa_assigned_to)
        self.assertEqual(pa.pr_assigned_to, self.officer_a)

    def test_unassign_pa_does_not_touch_pr(self):
        self.pr.assigned_to = self.officer_a
        self.pa.pa_assigned_to = self.officer_b
        self.pa.with_user(self.manager).action_assignment_unassign()
        self.assertFalse(self.pa.pa_assigned_to)
        self.assertEqual(self.pr.assigned_to, self.officer_a)

    def test_assign_pa_does_not_touch_pr(self):
        self.pr.assigned_to = self.officer_a
        self.pa.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(self.pa.pa_assigned_to, self.officer_b)
        self.assertEqual(self.pr.assigned_to, self.officer_a)

    # -- self claim --------------------------------------------------------
    def test_officer_claims_unassigned_pa(self):
        self.pa.with_user(self.officer_a).action_assignment_assign_me()
        self.assertEqual(self.pa.pa_assigned_to, self.officer_a)

    def test_self_claim_creates_no_activity(self):
        self.pa.with_user(self.officer_a).action_assignment_assign_me()
        self.assertFalse(self._todo_activities(self.pa, self.officer_a))

    def test_takeover_guard_blocks_second_officer(self):
        self.pa.pa_assigned_to = self.officer_a
        with self.assertRaises(UserError):
            self.pa.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(self.pa.pa_assigned_to, self.officer_a)

    def test_takeover_setting_allows_pa_takeover(self):
        self.env["ir.config_parameter"].sudo().set_param(TAKEOVER_PARAM, "True")
        self.pa.pa_assigned_to = self.officer_a
        self.pa.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(self.pa.pa_assigned_to, self.officer_b)

    # -- manager wizard ----------------------------------------------------
    def test_manager_assign_other_creates_todo_on_pa(self):
        wizard = self.Wizard.with_user(self.manager).create(
            {
                "res_model": "purchase.request.approval",
                "res_id": self.pa.id,
                "user_id": self.officer_a.id,
            }
        )
        wizard.action_assign()
        self.assertEqual(self.pa.pa_assigned_to, self.officer_a)
        self.assertTrue(self._todo_activities(self.pa, self.officer_a))
        # PR should not have a to-do from PA's assignment
        self.assertFalse(self._todo_activities(self.pr, self.officer_a))

    def test_manager_unassign_clears_field_and_activity(self):
        self.Wizard.with_user(self.manager).create(
            {
                "res_model": "purchase.request.approval",
                "res_id": self.pa.id,
                "user_id": self.officer_a.id,
            }
        ).action_assign()
        self.pa.with_user(self.manager).action_assignment_unassign()
        self.assertFalse(self.pa.pa_assigned_to)
        self.assertFalse(self._todo_activities(self.pa, self.officer_a))

    def test_user_cannot_unassign(self):
        self.pa.pa_assigned_to = self.officer_a
        with self.assertRaises(AccessError):
            self.pa.with_user(self.officer_a).action_assignment_unassign()

    # -- can_assign_me flag ------------------------------------------------
    def test_can_assign_me_flag_on_pa(self):
        self.assertTrue(
            self.pa.with_user(self.officer_a).assignment_can_assign_me
        )
        self.pa.with_user(self.officer_a).action_assignment_assign_me()
        self.assertFalse(
            self.pa.with_user(self.officer_a).assignment_can_assign_me
        )
        self.assertFalse(
            self.pa.with_user(self.officer_b).assignment_can_assign_me
        )
