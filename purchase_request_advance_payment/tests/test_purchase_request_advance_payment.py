from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestAdvancePayment(TransactionCase):
    """
    Test suite for the purchase_request_advance_payment bridge module.

    Covers the full flow: approved PR → loan picked in the loan app → link
    back on the PR → cross-post on disbursement (advance_payment ADR-0026). Tests avoid full accounting setup by setting states
    directly where needed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env.ref("base.user_admin")
        # The advance payment borrower is now hr.employee (ADR-0014); PR's
        # requested_by needs one to seed the loan's borrower. hr's
        # own data.xml already seeds hr.employee_admin with
        # user_id=base.user_admin on every database — reuse it instead of
        # creating a second one, which would violate hr_employee_user_uniq.
        cls.manager_employee = cls.env["hr.employee"].search(
            [("user_id", "=", cls.manager.id)], limit=1
        ) or cls.env["hr.employee"].create(
            {"name": cls.manager.name, "user_id": cls.manager.id}
        )

        # advance.payment.loan_verifier_id is required (ADR-0013); the admin
        # escape hatch is excluded from the auto-default candidate pool, so
        # the suite needs a real named officer for it to resolve.
        cls.officer = cls.env["res.users"].create(
            {
                "name": "Loan Officer",
                "login": "officer_pr_ap",
                "email": "officer_pr_ap@test.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref(
                                "advance_payment.group_advance_payment_loan_officer"
                            ).id
                        ],
                    )
                ],
            }
        )

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

    def _make_ap(self, pr, **vals):
        """Create a loan the way the borrower does: pick the PR on it."""
        return self.env["advance.payment"].create(
            {
                "employee_id": self.manager_employee.id,
                "loan_amount": 1000,
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
                "loan_reason": "Picker",
                "purchase_request_id": pr.id,
                **vals,
            }
        )

    # ------------------------------------------------------------------ #
    # Loan picked in the loan app (ADR-0026)                               #
    # ------------------------------------------------------------------ #

    def test_picked_loan_links_back_to_pr(self):
        pr = self._make_pr()
        self.assertEqual(pr.advance_payment_count, 0)
        ap = self._make_ap(pr)
        self.assertEqual(pr.advance_payment_id, ap)
        self.assertEqual(pr.advance_payment_count, 1)

    def test_smart_button_hidden_from_who_cannot_read_loan(self):
        """A PR reader with no right on the loan gets no button to an
        AccessError; the borrower still gets it."""
        pr = self._make_pr()
        self._make_ap(pr)
        self.assertTrue(pr.advance_payment_id)
        outsider = self.env["res.users"].create(
            {
                "name": "PR Reader",
                "login": "pr_reader_pr_ap",
                "email": "pr_reader_pr_ap@test.local",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertEqual(pr.with_user(outsider).advance_payment_count, 0)
        self.assertEqual(pr.with_user(self.manager).advance_payment_count, 1)

    def test_picking_pr_prefills_loan(self):
        pr = self._make_pr(estimated_cost=7500)
        pr.description = "Need it"
        ap = self.env["advance.payment"].new(
            {
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
                "purchase_request_id": pr.id,
            }
        )
        ap._onchange_purchase_request_id()
        self.assertEqual(ap.employee_id, pr.requested_by.employee_id)
        self.assertEqual(ap.loan_amount, 7500)
        self.assertIn("Need it", ap.loan_reason)

    def test_cancelled_loan_frees_pr(self):
        pr = self._make_pr()
        ap = self._make_ap(pr)
        ap.write({"state": "cancel"})
        self.assertFalse(pr.advance_payment_id)
        self.assertEqual(self._make_ap(pr), pr.advance_payment_id)

    def test_one_live_loan_per_pr(self):
        pr = self._make_pr()
        self._make_ap(pr)
        with self.assertRaises(ValidationError):
            self._make_ap(pr)

    def test_reset_cancelled_loan_refused_when_pr_taken(self):
        pr = self._make_pr()
        first = self._make_ap(pr)
        first.write({"state": "cancel"})
        self._make_ap(pr)
        with self.assertRaises(ValidationError):
            first.write({"state": "draft"})

    def test_picker_offers_only_free_advance_prs(self):
        free = self._make_pr()
        taken = self._make_pr()
        direct = self._make_pr(payment_type="direct")
        ap = self._make_ap(taken)
        probe = self.env["advance.payment"].new(
            {
                "employee_id": self.manager_employee.id,
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
            }
        )
        offered = self.env["purchase.request"].search(probe.reference_picker_domain)
        self.assertIn(free, offered)
        self.assertNotIn(taken, offered)
        self.assertNotIn(direct, offered)
        # The loan's own request stays offered on its own form.
        own = self.env["purchase.request"].search(ap.reference_picker_domain)
        self.assertIn(taken, own)

    # ------------------------------------------------------------------ #
    # Validation guards                                                    #
    # ------------------------------------------------------------------ #

    def test_pick_requires_approved_pr(self):
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
        with self.assertRaises(ValidationError):
            self._make_ap(pr)

    def test_pick_requires_advance_payment_type(self):
        pr = self._make_pr(payment_type="direct")
        with self.assertRaises(ValidationError):
            self._make_ap(pr)

    def test_pick_requires_requested_by_employee(self):
        """PR whose requested_by has no linked hr.employee cannot seed a loan —
        a readable UserError, not the required-field error (ADR-0014)."""
        no_employee_user = self.env["res.users"].create(
            {
                "name": "No Employee Requester",
                "login": "no_employee_requester_pr_ap",
                "email": "no_employee_requester_pr_ap@test.local",
            }
        )
        pr = self._make_pr()
        pr.requested_by = no_employee_user
        ap = self.env["advance.payment"].new({"purchase_request_id": pr.id})
        with self.assertRaises(UserError):
            ap._onchange_purchase_request_id()

    # ------------------------------------------------------------------ #
    # Cross-post on disbursement (action_start)                            #
    # ------------------------------------------------------------------ #

    def test_cross_post_on_disbursement(self):
        """When AP transitions to in_progress, a message is posted on the PR."""
        pr = self._make_pr()
        ap = self._make_ap(pr)
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
        ap = self._make_ap(self._make_pr())
        self.assertTrue(ap.is_locked_by_reference)

    def test_reference_not_locked_when_empty(self):
        """Reference is not locked when empty."""
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
    # Reference filter (advance_payment ADR-0023)                          #
    # ------------------------------------------------------------------ #

    def test_picker_domain_ands_type_filter_with_baseline(self):
        """The type's filter is evaluated for the borrower and ANDed with the
        bridge's approved-only baseline."""
        loan_type = self.env.ref("advance_payment.loan_type_procurement")
        loan_type.reference_domain = "[('requested_by', '=', user_id)]"
        pr = self._make_pr()
        other = self._make_pr()
        other.requested_by = self.officer
        ap = self.env["advance.payment"].create(
            {
                "employee_id": self.manager_employee.id,
                "loan_amount": 1000,
                "loan_type_id": loan_type.id,
                "loan_reason": "Picker",
            }
        )
        offered = self.env["purchase.request"].search(ap.reference_picker_domain)
        self.assertIn(pr, offered)
        self.assertNotIn(other, offered)
        self.assertFalse(offered.filtered(lambda r: r.state != "approved"))

    def test_draft_check_rejects_reference_outside_filter(self):
        loan_type = self.env.ref("advance_payment.loan_type_procurement")
        loan_type.reference_domain = "[('id', '=', 0)]"
        pr = self._make_pr()
        with self.assertRaises(ValidationError):
            self._make_ap(pr)

    def test_picker_writes_reference(self):
        pr = self._make_pr()
        ap = self._make_ap(pr)
        self.assertEqual(ap.reference, pr)
        # Not left stale by the picker's inverse (excep_missing_reference
        # reads it).
        self.assertEqual(ap.reference_model, "purchase.request")

    # ------------------------------------------------------------------ #
    # View action                                                          #
    # ------------------------------------------------------------------ #

    def test_action_view_advance_payment(self):
        """Smart button returns correct action to open AP form."""
        pr = self._make_pr()
        self._make_ap(pr)
        result = pr.action_view_advance_payment()
        self.assertEqual(result["res_model"], "advance.payment")
        self.assertEqual(result["res_id"], pr.advance_payment_id.id)
        self.assertEqual(result["view_mode"], "form")
