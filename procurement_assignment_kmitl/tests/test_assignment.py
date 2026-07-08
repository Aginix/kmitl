# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

# Keep constants local — the mixin now lives in base_assignment and the
# consumer exposes its parameter key through _assignment_takeover_param().
ASSIGN_ACTIVITY_XMLID = "base_assignment.mail_activity_assignment"
TAKEOVER_PARAM = "procurement_assignment_kmitl.allow_takeover_assigned"


@tagged("post_install", "-at_install")
class TestProcurementAssignment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PR = cls.env["purchase.request"]
        cls.Wizard = cls.env["assign.officer.wizard"]

        users = cls.env["res.users"].with_context(no_reset_password=True)
        g_pr_user_all = cls.env.ref(
            "purchase_request_kmitl.group_purchase_request_user_all"
        )
        g_pr_manager = cls.env.ref(
            "purchase_request.group_purchase_request_manager"
        )
        g_po_user = cls.env.ref("purchase.group_purchase_user")
        g_po_manager = cls.env.ref("purchase.group_purchase_manager")

        cls.officer_a = users.create(
            {
                "name": "Officer A",
                "login": "pa_officer_a",
                "groups_id": [(6, 0, [g_pr_user_all.id, g_po_user.id])],
            }
        )
        cls.officer_b = users.create(
            {
                "name": "Officer B",
                "login": "pa_officer_b",
                "groups_id": [(6, 0, [g_pr_user_all.id, g_po_user.id])],
            }
        )
        cls.manager = users.create(
            {
                "name": "PA Manager",
                "login": "pa_manager",
                "groups_id": [(6, 0, [g_pr_manager.id, g_po_manager.id])],
            }
        )
        cls.outsider = users.create(
            {
                "name": "Outsider",
                "login": "pa_outsider",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

        picking_type = cls.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        cls.pr = cls.PR.create({"picking_type_id": picking_type.id})

    def _todo_activities(self, record, user):
        todo = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        return record.activity_ids.filtered(
            lambda a: a.user_id == user and a.activity_type_id == todo
        )

    # -- self claim --------------------------------------------------------
    def test_user_claims_unassigned(self):
        self.pr.with_user(self.officer_a).action_assignment_assign_me()
        self.assertEqual(self.pr.assigned_to, self.officer_a)

    def test_self_assign_creates_no_activity(self):
        self.pr.with_user(self.officer_a).action_assignment_assign_me()
        self.assertFalse(self._todo_activities(self.pr, self.officer_a))

    def test_user_cannot_take_over_when_restricted(self):
        self.pr.assigned_to = self.officer_a
        with self.assertRaises(UserError):
            self.pr.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(self.pr.assigned_to, self.officer_a)

    def test_takeover_setting_allows_steal(self):
        self.env["ir.config_parameter"].sudo().set_param(TAKEOVER_PARAM, "True")
        self.pr.assigned_to = self.officer_a
        self.pr.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(self.pr.assigned_to, self.officer_b)

    # -- manager assigns others -------------------------------------------
    def test_manager_assign_other_creates_activity(self):
        wizard = self.Wizard.with_user(self.manager).create(
            {
                "res_model": "purchase.request",
                "res_id": self.pr.id,
                "user_id": self.officer_a.id,
            }
        )
        wizard.action_assign()
        self.assertEqual(self.pr.assigned_to, self.officer_a)
        self.assertTrue(self._todo_activities(self.pr, self.officer_a))

    def test_reassign_clears_previous_activity(self):
        wizard_a = self.Wizard.with_user(self.manager).create(
            {
                "res_model": "purchase.request",
                "res_id": self.pr.id,
                "user_id": self.officer_a.id,
            }
        )
        wizard_a.action_assign()
        wizard_b = self.Wizard.with_user(self.manager).create(
            {
                "res_model": "purchase.request",
                "res_id": self.pr.id,
                "user_id": self.officer_b.id,
            }
        )
        wizard_b.action_assign()
        self.assertEqual(self.pr.assigned_to, self.officer_b)
        self.assertFalse(self._todo_activities(self.pr, self.officer_a))
        self.assertTrue(self._todo_activities(self.pr, self.officer_b))

    # -- unassign ----------------------------------------------------------
    def test_manager_unassign_clears_field_and_activity(self):
        self.Wizard.with_user(self.manager).create(
            {
                "res_model": "purchase.request",
                "res_id": self.pr.id,
                "user_id": self.officer_a.id,
            }
        ).action_assign()
        self.pr.with_user(self.manager).action_assignment_unassign()
        self.assertFalse(self.pr.assigned_to)
        self.assertFalse(self._todo_activities(self.pr, self.officer_a))

    def test_user_cannot_unassign(self):
        self.pr.assigned_to = self.officer_a
        with self.assertRaises(AccessError):
            self.pr.with_user(self.officer_a).action_assignment_unassign()

    def test_user_cannot_open_assign_wizard(self):
        with self.assertRaises(AccessError):
            self.pr.with_user(self.officer_a).action_assignment_open_wizard()

    # -- wizard domain -----------------------------------------------------
    def test_wizard_allowed_users_restricted_to_officer_group(self):
        wizard = self.Wizard.with_user(self.manager).create(
            {"res_model": "purchase.request", "res_id": self.pr.id}
        )
        self.assertIn(self.officer_a, wizard.allowed_user_ids)
        self.assertNotIn(self.outsider, wizard.allowed_user_ids)

    # -- can_assign_me flag ------------------------------------------------
    def test_can_assign_me_flag(self):
        # unassigned -> True for an officer
        flag = self.pr.with_user(self.officer_a).assignment_can_assign_me
        self.assertTrue(flag)
        # assigned to self -> False
        self.pr.with_user(self.officer_a).action_assignment_assign_me()
        self.assertFalse(self.pr.with_user(self.officer_a).assignment_can_assign_me)
        # assigned to someone else, restricted -> False for another officer
        self.assertFalse(
            self.pr.with_user(self.officer_b).assignment_can_assign_me
        )
