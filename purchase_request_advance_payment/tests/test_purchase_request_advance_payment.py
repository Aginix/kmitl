from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestAdvancePayment(TransactionCase):
    """
    Test suite for the purchase_request_advance_payment bridge module.

    Covers the full flow: approved PR → create advance payment → cross-post
    on disbursement. Tests avoid full accounting setup by setting states
    directly where needed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env.ref("base.user_admin")

        # Fiscal year
        cls.fiscal_year = cls.env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            from datetime import date

            cls.fiscal_year = cls.env["account.fiscal.year"].create(
                {
                    "name": "2568",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                }
            )

        # Procurement type
        cls.procurement_type = cls.env["procurement.type"].search([], limit=1)
        if not cls.procurement_type:
            cls.procurement_type = cls.env["procurement.type"].create(
                {"name": "Test Procurement"}
            )

        # Procurement method
        cls.procurement_method = cls.env["procurement.method"].search([], limit=1)
        if not cls.procurement_method:
            cls.procurement_method = cls.env["procurement.method"].create(
                {"name": "Test Method"}
            )

        # Analytic plans (for analytic_distribution)
        cls.plan_activities = cls.env.ref(
            "account_analytic_kmitl.analytic_plan_activities"
        )
        cls.plan_departments = cls.env.ref(
            "account_analytic_kmitl.analytic_plan_departments"
        )
        cls.plan_funds = cls.env.ref("account_analytic_kmitl.analytic_plan_funds")
        cls.plan_sources = cls.env.ref("account_analytic_kmitl.analytic_plan_sources")

        cls.activity_account = cls.env["account.analytic.account"].create(
            {"name": "Test Activity", "plan_id": cls.plan_activities.id}
        )
        cls.department_account = cls.env["account.analytic.account"].create(
            {"name": "Test Department", "plan_id": cls.plan_departments.id}
        )
        cls.fund_account = cls.env["account.analytic.account"].create(
            {"name": "Test Fund", "plan_id": cls.plan_funds.id}
        )
        cls.source_account = cls.env["account.analytic.account"].create(
            {"name": "Test Source", "plan_id": cls.plan_sources.id}
        )

        cls.analytic_distribution = {
            str(cls.activity_account.id): 100,
            str(cls.department_account.id): 100,
            str(cls.fund_account.id): 100,
            str(cls.source_account.id): 100,
        }

    def _make_pr(self, payment_type="advance", estimated_cost=5000):
        """Create an approved purchase request with the given payment type."""
        pr = self.env["purchase.request"].create(
            {
                "title": "Test PR for Advance",
                "requested_by": self.manager.id,
                "account_fiscal_year_id": self.fiscal_year.id,
                "procurement_type_id": self.procurement_type.id,
                "procurement_method_id": self.procurement_method.id,
                "payment_type": payment_type,
                "analytic_distribution": self.analytic_distribution,
            }
        )
        # Add a line so estimated_cost is populated
        self.env["purchase.request.line"].create(
            {
                "request_id": pr.id,
                "name": "Test Line",
                "product_qty": 1,
                "estimated_cost": estimated_cost,
            }
        )
        # Approve the PR (draft → to_approve → approved)
        pr.button_to_approve()
        pr.with_user(self.manager).button_approved()
        return pr

    # ------------------------------------------------------------------ #
    # Create advance payment from PR                                       #
    # ------------------------------------------------------------------ #

    def test_create_ap_from_pr(self):
        """Approved PR with payment_type=advance can create advance payment."""
        pr = self._make_pr()
        result = pr.action_create_advance_payment()
        ap = pr.advance_payment_id
        self.assertTrue(ap)
        self.assertEqual(ap.state, "draft")
        self.assertEqual(result["res_model"], "advance.payment")
        self.assertEqual(result["res_id"], ap.id)

    def test_ap_fields_populated_from_pr(self):
        """AP gets correct values from PR."""
        pr = self._make_pr(estimated_cost=7500)
        pr.action_create_advance_payment()
        ap = pr.advance_payment_id
        self.assertEqual(ap.requested_by, pr.requested_by)
        self.assertEqual(ap.loan_amount, 7500)
        self.assertEqual(
            ap.loan_type_id,
            self.env.ref("advance_payment.loan_type_procurement"),
        )
        self.assertEqual(ap.loan_reason, pr.title)
        self.assertEqual(
            ap.reference, "purchase.request,%s" % pr.id
        )

    def test_ap_analytic_distribution_from_pr(self):
        """AP inherits analytic_distribution from PR header."""
        pr = self._make_pr()
        pr.action_create_advance_payment()
        ap = pr.advance_payment_id
        self.assertEqual(ap.analytic_distribution, self.analytic_distribution)

    def test_pr_message_posted_on_create(self):
        """PR chatter gets a message when AP is created."""
        pr = self._make_pr()
        msg_count_before = len(pr.message_ids)
        pr.action_create_advance_payment()
        self.assertGreater(len(pr.message_ids), msg_count_before)

    def test_pr_smart_button_count(self):
        """advance_payment_count reflects linked AP."""
        pr = self._make_pr()
        self.assertEqual(pr.advance_payment_count, 0)
        pr.action_create_advance_payment()
        self.assertEqual(pr.advance_payment_count, 1)

    # ------------------------------------------------------------------ #
    # Validation guards                                                    #
    # ------------------------------------------------------------------ #

    def test_create_ap_requires_approved_state(self):
        """Cannot create AP from non-approved PR."""
        pr = self.env["purchase.request"].create(
            {
                "title": "Draft PR",
                "requested_by": self.manager.id,
                "account_fiscal_year_id": self.fiscal_year.id,
                "procurement_type_id": self.procurement_type.id,
                "procurement_method_id": self.procurement_method.id,
                "payment_type": "advance",
            }
        )
        with self.assertRaises(UserError):
            pr.action_create_advance_payment()

    def test_create_ap_requires_advance_payment_type(self):
        """Cannot create AP when payment_type is not 'advance'."""
        pr = self._make_pr(payment_type="direct")
        with self.assertRaises(UserError):
            pr.action_create_advance_payment()

    def test_create_ap_only_once(self):
        """Cannot create a second AP for the same PR."""
        pr = self._make_pr()
        pr.action_create_advance_payment()
        with self.assertRaises(UserError):
            pr.action_create_advance_payment()

    # ------------------------------------------------------------------ #
    # Cross-post on disbursement (action_start)                            #
    # ------------------------------------------------------------------ #

    def test_cross_post_on_disbursement(self):
        """When AP transitions to in_progress, a message is posted on the PR."""
        pr = self._make_pr()
        pr.action_create_advance_payment()
        ap = pr.advance_payment_id
        # Simulate approval + disbursement (bypass actual payment creation)
        ap.write({"state": "approved", "disbursement_state": "pending"})
        msg_count_before = len(pr.message_ids)
        ap.action_start()
        pr.invalidate_recordset()
        self.assertGreater(len(pr.message_ids), msg_count_before)

    def test_no_cross_post_without_reference(self):
        """AP without reference does not post to any PR."""
        ap = self.env["advance.payment"].create(
            {
                "requested_by": self.manager.id,
                "loan_amount": 1000,
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
                "loan_reason": "Standalone",
            }
        )
        ap.write({"state": "approved"})
        # Should not raise even without reference
        ap.action_start()
        self.assertEqual(ap.state, "in_progress")

    # ------------------------------------------------------------------ #
    # is_locked_by_reference / is_reference_visible                        #
    # ------------------------------------------------------------------ #

    def test_reference_locked_when_set(self):
        """Reference field is locked when it has a value (from PR)."""
        pr = self._make_pr()
        pr.action_create_advance_payment()
        ap = pr.advance_payment_id
        self.assertTrue(ap.is_locked_by_reference)

    def test_reference_not_locked_when_empty(self):
        """Reference is not locked when empty."""
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.allow_manual_reference", "True"
        )
        ap = self.env["advance.payment"].create(
            {
                "requested_by": self.manager.id,
                "loan_amount": 1000,
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
                "loan_reason": "Standalone",
            }
        )
        self.assertFalse(ap.is_locked_by_reference)

    def test_reference_visible_when_loan_type_has_model(self):
        """Reference is visible when loan type has a reference_model."""
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.allow_manual_reference", "False"
        )
        ap = self.env["advance.payment"].create(
            {
                "requested_by": self.manager.id,
                "loan_amount": 1000,
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
                "loan_reason": "Standalone",
            }
        )
        self.assertTrue(ap.is_reference_visible)

    # ------------------------------------------------------------------ #
    # View action                                                          #
    # ------------------------------------------------------------------ #

    def test_action_view_advance_payment(self):
        """Smart button returns correct action to open AP form."""
        pr = self._make_pr()
        pr.action_create_advance_payment()
        result = pr.action_view_advance_payment()
        self.assertEqual(result["res_model"], "advance.payment")
        self.assertEqual(result["res_id"], pr.advance_payment_id.id)
        self.assertEqual(result["view_mode"], "form")
