# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.account_payment import (
    ASSIGN_ACTIVITY_XMLID,
    TAKEOVER_PARAM,
)


@tagged("post_install", "-at_install")
class TestFinanceAssignment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Payment = cls.env["account.payment"]
        cls.Rule = cls.env["finance.assignment.rule"]
        cls.Wizard = cls.env["finance.assign.officer.wizard"]

        # -- analytic dimensions ----------------------------------------
        AAA = cls.env["account.analytic.account"]
        dep_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_departments")
        src_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_sources")
        fund_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_funds")
        act_plan = cls.env.ref("account_analytic_kmitl.analytic_plan_activities")

        cls.dept_parent = AAA.create({"name": "Faculty", "plan_id": dep_plan.id})
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
        cls.source_rev = AAA.create({"name": "Revenue Budget", "plan_id": src_plan.id})
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

        # -- payment plumbing --------------------------------------------
        cls.payment_type_out = cls.env.ref("finance_kmitl.payment_type_normal_outbound")
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create(
                {"name": "Test Bank", "code": "TBNK", "type": "bank"}
            )

        # Two seeded หัวจ่าย on ใบสำคัญจ่าย (PV). A voucher takes its journal
        # from the paying account, so the helper below swaps both together.
        cls.paying_scb = cls.env.ref(
            "account_kmitl.paying_account_1112210004_transfer"
        )
        cls.paying_ktb = cls.env.ref(
            "account_kmitl.paying_account_1112120002_transfer"
        )

        # -- users -------------------------------------------------------
        users = cls.env["res.users"].with_context(no_reset_password=True)
        g_officer = cls.env.ref("finance_kmitl.group_finance_kmitl_user_out")
        g_manager = cls.env.ref("finance_kmitl.group_finance_kmitl_manager")
        g_user = cls.env.ref("base.group_user")
        cls.officer_a = users.create(
            {
                "name": "Officer A",
                "login": "fin_officer_a",
                "groups_id": [(6, 0, [g_officer.id])],
            }
        )
        cls.officer_b = users.create(
            {
                "name": "Officer B",
                "login": "fin_officer_b",
                "groups_id": [(6, 0, [g_officer.id])],
            }
        )
        cls.manager = users.create(
            {
                "name": "Finance Manager",
                "login": "fin_manager",
                "groups_id": [(6, 0, [g_manager.id])],
            }
        )
        cls.outsider = users.create(
            {
                "name": "Outsider",
                "login": "fin_outsider",
                "groups_id": [(6, 0, [g_user.id])],
            }
        )

    # -- helpers ---------------------------------------------------------
    def _payment_vals(self, department, source, partner, paying_account=None):
        vals = {
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": partner.id,
            "amount": 100.0,
            "date": fields.Date.today(),
            "journal_id": self.bank_journal.id,
            "kmitl_payment_type_id": self.payment_type_out.id,
            "department_analytic_id": department.id,
            "source_analytic_id": source.id,
            "fund_analytic_id": self.fund_a.id,
            "activity_analytic_id": self.activity_a.id,
        }
        if paying_account:
            # The paying account belongs to exactly one journal, so taking the
            # journal from it is what keeps the two from disagreeing.
            vals["journal_id"] = paying_account.journal_id.id
            vals["payment_method_line_id"] = paying_account.id
        return vals

    def _make_payment(
        self,
        source=None,
        department=None,
        partner=None,
        create_as=None,
        paying_account=None,
    ):
        """A voucher filled in on the form: the dimension fields are written."""
        vals = self._payment_vals(
            department or self.dept_child,
            source or self.source_gov,
            partner or self.partner_a,
            paying_account=paying_account,
        )
        payments = self.Payment
        if create_as:
            payments = payments.with_user(create_as)
        return payments.create(vals)

    def _make_payment_from_distribution(self, department=None, source=None):
        """A voucher created the way a disbursement request creates one.

        ``disbursement.request._create_payments`` passes ``analytic_distribution``
        copied off the bill rather than the individual dimension fields, so the
        dimensions only exist once the mixin's inverse has run.
        """
        department = department or self.dept_child
        source = source or self.source_gov
        vals = self._payment_vals(department, source, self.partner_a)
        for name in (
            "department_analytic_id",
            "source_analytic_id",
            "fund_analytic_id",
            "activity_analytic_id",
        ):
            del vals[name]
        vals["analytic_distribution"] = {
            str(department.id): 100,
            str(source.id): 100,
            str(self.fund_a.id): 100,
            str(self.activity_a.id): 100,
        }
        return self.Payment.create(vals)

    def _todos(self, record, user):
        todo = self.env.ref(ASSIGN_ACTIVITY_XMLID)
        summary = record._assignment_activity_summary()
        return record.activity_ids.filtered(
            lambda a: a.user_id == user
            and a.activity_type_id == todo
            and a.summary == summary
        )

    def _reassign(self, payment, user):
        self.Wizard.with_user(self.manager).create(
            {"payment_id": payment.id, "user_id": user.id}
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
        payment = self._make_payment(partner=self.partner_a)
        self.assertEqual(payment.assigned_to, self.officer_a)
        self.assertTrue(self._todos(payment, self.officer_a))

    def test_wildcard_rule_matches(self):
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment()
        self.assertEqual(payment.assigned_to, self.officer_a)

    def test_and_of_multiple_criteria(self):
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_child.id,
                "source_analytic_id": self.source_gov.id,
            }
        )
        matched = self._make_payment(
            department=self.dept_child, source=self.source_gov
        )
        self.assertEqual(matched.assigned_to, self.officer_a)
        missed = self._make_payment(
            department=self.dept_child, source=self.source_rev
        )
        self.assertFalse(missed.assigned_to)

    def test_parent_rule_covers_child(self):
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_parent.id,
            }
        )
        payment = self._make_payment(department=self.dept_child)
        self.assertEqual(payment.assigned_to, self.officer_a)

    def test_child_rule_does_not_cover_parent(self):
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_child.id,
            }
        )
        payment = self._make_payment(department=self.dept_parent)
        self.assertFalse(payment.assigned_to)

    def test_sequence_decides_first_match(self):
        self.Rule.create({"user_id": self.officer_a.id, "sequence": 5})
        self.Rule.create({"user_id": self.officer_b.id, "sequence": 1})
        payment = self._make_payment()
        self.assertEqual(payment.assigned_to, self.officer_b)

    def test_partner_type_match_and_mismatch(self):
        self.Rule.create(
            {"user_id": self.officer_a.id, "partner_type_id": self.pt_a.id}
        )
        self.Rule.create({"user_id": self.officer_b.id})
        payment_a = self._make_payment(partner=self.partner_a)
        self.assertEqual(payment_a.assigned_to, self.officer_a)
        payment_b = self._make_payment(partner=self.partner_b)
        self.assertEqual(payment_b.assigned_to, self.officer_b)

    def test_paying_account_match_and_mismatch(self):
        """A rule on a หัวจ่าย routes only the vouchers paid from it."""
        self.Rule.create(
            {"user_id": self.officer_a.id, "paying_account_id": self.paying_ktb.id}
        )
        self.Rule.create({"user_id": self.officer_b.id})
        from_ktb = self._make_payment(paying_account=self.paying_ktb)
        self.assertEqual(from_ktb.assigned_to, self.officer_a)
        from_scb = self._make_payment(paying_account=self.paying_scb)
        self.assertEqual(from_scb.assigned_to, self.officer_b)

    def test_empty_paying_account_is_a_wildcard(self):
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment(paying_account=self.paying_ktb)
        self.assertEqual(payment.assigned_to, self.officer_a)

    def test_paying_account_ands_with_the_dimensions(self):
        """หัวจ่าย narrows alongside the other criteria, it does not override them."""
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_parent.id,
                "paying_account_id": self.paying_ktb.id,
            }
        )
        matched = self._make_payment(
            department=self.dept_child, paying_account=self.paying_ktb
        )
        self.assertEqual(matched.assigned_to, self.officer_a)
        # Right account, wrong department.
        other_faculty = self.env["account.analytic.account"].create(
            {"name": "Other Faculty", "plan_id": self.dept_parent.plan_id.id}
        )
        missed = self._make_payment(
            department=other_faculty, paying_account=self.paying_ktb
        )
        self.assertFalse(missed.assigned_to)

    def test_the_voucher_carries_the_payee_type_it_is_routed_by(self):
        """``payee_type_id`` is the list's side of the rule's ``partner_type_id``.

        It belongs to ``finance_kmitl`` — the finance list filters and groups by
        it — but it is asserted here because this is where the partners that
        carry a type are set up, and because a rule matching on a type the
        voucher does not report would route by one thing and be searched by
        another.
        """
        payment = self._make_payment(partner=self.partner_a)
        self.assertEqual(payment.payee_type_id, self.pt_a)
        # Stored and related, so it follows the payee rather than freezing.
        payment.partner_id = self.partner_b
        self.assertEqual(payment.payee_type_id, self.pt_b)

    def test_no_rule_leaves_unassigned(self):
        payment = self._make_payment()
        self.assertFalse(payment.assigned_to)

    def test_inactive_rule_skipped(self):
        self.Rule.create({"user_id": self.officer_a.id, "active": False})
        payment = self._make_payment()
        self.assertFalse(payment.assigned_to)

    def test_archived_officer_skipped(self):
        self.officer_a.active = False
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment()
        self.assertFalse(payment.assigned_to)

    # -- both ways a voucher comes into being ----------------------------
    def test_distribution_only_create_is_routed(self):
        """The disbursement path passes analytic_distribution, not the fields."""
        self.Rule.create(
            {
                "user_id": self.officer_a.id,
                "department_analytic_id": self.dept_parent.id,
            }
        )
        payment = self._make_payment_from_distribution()
        self.assertEqual(payment.department_analytic_id, self.dept_child)
        self.assertEqual(payment.assigned_to, self.officer_a)

    def test_inbound_payment_is_not_routed(self):
        self.Rule.create({"user_id": self.officer_a.id})
        inbound = self.Payment.create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 100.0,
                "date": fields.Date.today(),
                "journal_id": self.bank_journal.id,
                "kmitl_payment_type_id": self.env.ref(
                    "finance_kmitl.payment_type_normal_inbound"
                ).id,
                "department_analytic_id": self.dept_child.id,
                "source_analytic_id": self.source_gov.id,
                "fund_analytic_id": self.fund_a.id,
                "activity_analytic_id": self.activity_a.id,
            }
        )
        self.assertFalse(inbound.assigned_to)

    # -- notify / self-create --------------------------------------------
    def test_self_create_makes_no_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment(create_as=self.officer_a)
        self.assertEqual(payment.assigned_to, self.officer_a)
        self.assertFalse(self._todos(payment, self.officer_a))

    # -- manual override --------------------------------------------------
    def test_manager_reassign_moves_the_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment()
        self.assertEqual(payment.assigned_to, self.officer_a)
        self._reassign(payment, self.officer_b)
        self.assertEqual(payment.assigned_to, self.officer_b)
        self.assertFalse(self._todos(payment, self.officer_a))
        self.assertEqual(len(self._todos(payment, self.officer_b)), 1)

    # -- the finance office is done ---------------------------------------
    def test_mark_paid_closes_the_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment()
        self.assertTrue(self._todos(payment, self.officer_a))
        payment.finance_state = "confirmed"
        payment._mark_paid()
        self.assertEqual(payment.finance_state, "paid")
        self.assertFalse(self._todos(payment, self.officer_a))
        # The officer who carried it stays on the record.
        self.assertEqual(payment.assigned_to, self.officer_a)

    def test_cancel_closes_the_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment()
        self.assertTrue(self._todos(payment, self.officer_a))
        payment.action_cancel()
        self.assertFalse(self._todos(payment, self.officer_a))

    def test_assignment_survives_confirmation(self):
        """``assigned_to`` is not part of the frozen money side."""
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment()
        payment.finance_state = "confirmed"
        self._reassign(payment, self.officer_b)
        self.assertEqual(payment.assigned_to, self.officer_b)

    # -- takeover guard ----------------------------------------------------
    def test_takeover_default_true_allows_claim(self):
        payment = self._make_payment()
        payment.assigned_to = self.officer_a
        payment.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(payment.assigned_to, self.officer_b)

    def test_takeover_disabled_blocks_claim(self):
        self.env["ir.config_parameter"].sudo().set_param(TAKEOVER_PARAM, "False")
        payment = self._make_payment()
        payment.assigned_to = self.officer_a
        with self.assertRaises(UserError):
            payment.with_user(self.officer_b).action_assignment_assign_me()
        self.assertEqual(payment.assigned_to, self.officer_a)

    def test_can_claim_logic(self):
        payment = self._make_payment()
        self.assertTrue(payment.with_user(self.officer_a).assignment_can_assign_me)
        payment.assigned_to = self.officer_a
        self.assertFalse(payment.with_user(self.officer_a)._assignment_can_claim())
        # takeover default True -> another officer may still claim
        self.assertTrue(payment.with_user(self.officer_b)._assignment_can_claim())
        self.env["ir.config_parameter"].sudo().set_param(TAKEOVER_PARAM, "False")
        self.assertFalse(payment.with_user(self.officer_b)._assignment_can_claim())

    # -- manager-only actions ----------------------------------------------
    def test_manager_unassign_clears_field_and_todo(self):
        self.Rule.create({"user_id": self.officer_a.id})
        payment = self._make_payment()
        payment.with_user(self.manager).action_assignment_unassign()
        self.assertFalse(payment.assigned_to)
        self.assertFalse(self._todos(payment, self.officer_a))

    def test_user_cannot_unassign(self):
        payment = self._make_payment()
        payment.assigned_to = self.officer_a
        with self.assertRaises(AccessError):
            payment.with_user(self.officer_a).action_assignment_unassign()

    def test_user_cannot_open_wizard(self):
        payment = self._make_payment()
        with self.assertRaises(AccessError):
            payment.with_user(self.officer_a).action_assignment_open_wizard()

    # -- wizard -------------------------------------------------------------
    def test_wizard_allowed_users_are_officer_group(self):
        payment = self._make_payment()
        wiz = self.Wizard.with_user(self.manager).create(
            {"payment_id": payment.id, "user_id": self.officer_a.id}
        )
        self.assertIn(self.officer_a, wiz.allowed_user_ids)
        self.assertNotIn(self.outsider, wiz.allowed_user_ids)

    # -- re-apply to backlog ------------------------------------------------
    def test_apply_to_pending_assigns_only_empty(self):
        empty = self._make_payment()
        self.assertFalse(empty.assigned_to)
        taken = self._make_payment()
        taken.assigned_to = self.officer_b
        self.Rule.create({"user_id": self.officer_a.id})
        self.Rule.action_apply_to_pending()
        self.assertEqual(empty.assigned_to, self.officer_a)
        self.assertEqual(taken.assigned_to, self.officer_b)

    def test_apply_to_pending_ignores_archived_rule(self):
        payment = self._make_payment()
        self.assertFalse(payment.assigned_to)
        rule = self.Rule.create({"user_id": self.officer_a.id})
        rule.active = False
        # The gear-menu action leaks active_test=False into the server action;
        # matching must still skip archived rules.
        self.Rule.with_context(active_test=False).action_apply_to_pending()
        self.assertFalse(payment.assigned_to)

    def test_apply_to_pending_skips_paid_vouchers(self):
        payment = self._make_payment()
        payment.finance_state = "confirmed"
        payment._mark_paid()
        self.Rule.create({"user_id": self.officer_a.id})
        self.Rule.action_apply_to_pending()
        self.assertFalse(payment.assigned_to)
