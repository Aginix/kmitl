from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseRequestAdvancePayment(TransactionCase):
    """
    Test suite for the purchase_request_advance_payment bridge module.

    Covers the full flow: approved PR → loan naming it in the loan app → link
    back on the PR → cross-post on disbursement (advance_payment ADR-0029).
    Tests avoid full accounting setup by setting states directly where
    needed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = cls.env.ref("base.user_admin")
        # The advance payment borrower is now hr.employee (ADR-0014). hr's
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
        """Create a loan the way the borrower does: type the PR's number."""
        return self.env["advance.payment"].create(
            {
                "employee_id": self.manager_employee.id,
                "loan_amount": 1000,
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
                "loan_reason": "Picker",
                "reference_number": pr.name,
                **vals,
            }
        )

    # ------------------------------------------------------------------ #
    # Loan made in the loan app, by the PR's number (ADR-0029)             #
    # ------------------------------------------------------------------ #

    def test_loan_links_back_to_pr(self):
        pr = self._make_pr()
        self.assertEqual(pr.advance_payment_count, 0)
        ap = self._make_ap(pr)
        self.assertEqual(ap.purchase_request_id, pr)
        self.assertEqual(pr.advance_payment_ids, ap)
        self.assertEqual(pr.advance_payment_count, 1)

    def test_several_borrowers_per_pr(self):
        """One person holds one agreement, so a team splits a request
        (ADR-0029): a second loan on the same PR is allowed."""
        pr = self._make_pr()
        first = self._make_ap(pr)
        other_employee = self.env["hr.employee"].create({"name": "Second Borrower"})
        second = self._make_ap(pr, employee_id=other_employee.id)
        self.assertEqual(pr.advance_payment_ids, first | second)
        self.assertTrue(second.has_other_purchase_request_loan)
        # ADR-0026's single-loan rule ships switched off (ADR-0030).
        self.assertFalse(
            self.env.ref("purchase_request_advance_payment.excep_pr_single_loan").active
        )

    def test_borrower_without_pr_access_finds_it_by_number(self):
        """The lookup runs under sudo: a borrower who cannot read the PR
        still names it (ADR-0029)."""
        pr = self._make_pr()
        borrower = self.env["res.users"].create(
            {
                "name": "Own-only Borrower",
                "login": "own_only_pr_ap",
                "groups_id": [
                    (
                        6,
                        0,
                        self.env.ref(
                            "advance_payment.group_advance_payment_own_only"
                        ).ids,
                    )
                ],
            }
        )
        self.assertFalse(
            self.env["purchase.request"]
            .with_user(borrower)
            .check_access_rights("read", raise_exception=False)
        )
        probe = (
            self.env["advance.payment"]
            .with_user(borrower)
            .new(
                {
                    "loan_type_id": self.env.ref(
                        "advance_payment.loan_type_procurement"
                    ).id,
                }
            )
        )
        self.assertEqual(probe._find_reference_by_number(pr.name), pr)
        self.assertEqual(
            probe._find_reference_by_number("  %s  " % pr.name.lower()), pr
        )
        self.assertFalse(probe._find_reference_by_number("NO-SUCH-NUMBER"))
        self.assertFalse(probe._find_reference_by_number("%"))

    def test_smart_button_hidden_from_who_cannot_read_loan(self):
        """A PR reader with no right on the loan gets no button to an
        AccessError; the borrower still gets it."""
        pr = self._make_pr()
        self._make_ap(pr)
        self.assertTrue(pr.advance_payment_ids)
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

    def test_typing_pr_number_prefills_loan_and_keeps_borrower(self):
        """Anyone may borrow against a request, not only its requester: the
        amount and reason come from the PR, the borrower stays (ADR-0029)."""
        pr = self._make_pr(estimated_cost=7500)
        pr.description = "Need it"
        pr.requested_by = self.officer
        ap = self.env["advance.payment"].new(
            {
                "employee_id": self.manager_employee.id,
                "loan_type_id": self.env.ref(
                    "advance_payment.loan_type_procurement"
                ).id,
                "reference_number": pr.name,
            }
        )
        ap._onchange_reference_number()
        self.assertEqual(ap.reference, pr)
        self.assertEqual(ap.employee_id, self.manager_employee)
        self.assertEqual(ap.loan_amount, 7500)
        self.assertIn("Need it", ap.loan_reason)

    # ------------------------------------------------------------------ #
    # Borrowing rules (ADR-0030): flags, not constraints                   #
    # ------------------------------------------------------------------ #

    def test_unapproved_pr_flagged(self):
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
        ap = self._make_ap(pr)
        self.assertFalse(ap.is_purchase_request_approved)

    def test_non_advance_pr_flagged(self):
        ap = self._make_ap(self._make_pr(payment_type="direct"))
        self.assertTrue(ap.is_purchase_request_approved)
        self.assertFalse(ap.is_purchase_request_advance)

    # ------------------------------------------------------------------ #
    # Cross-post on disbursement (action_start)                            #
    # ------------------------------------------------------------------ #

    def test_cross_post_on_disbursement(self):
        """When AP transitions to in_progress, a message is posted on the PR."""
        pr = self._make_pr()
        ap = self._make_ap(pr)
        # Simulate approval + disbursement (bypass actual payment creation)
        ap.write({"state": "approved"})
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

    def test_lookup_respects_type_filter(self):
        """The type's filter is evaluated for the borrower and bounds the
        number lookup."""
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
        self.assertEqual(ap._find_reference_by_number(pr.name), pr)
        self.assertFalse(ap._find_reference_by_number(other.name))
        with self.assertRaises(ValidationError):
            self._make_ap(other)

    def test_draft_check_rejects_reference_outside_filter(self):
        loan_type = self.env.ref("advance_payment.loan_type_procurement")
        loan_type.reference_domain = "[('id', '=', 0)]"
        pr = self._make_pr()
        with self.assertRaises(ValidationError):
            self._make_ap(pr)

    def test_number_writes_reference(self):
        pr = self._make_pr()
        ap = self._make_ap(pr)
        self.assertEqual(ap.reference, pr)
        # Not left stale by the number's inverse (excep_missing_reference
        # reads it).
        self.assertEqual(ap.reference_model, "purchase.request")

    # ------------------------------------------------------------------ #
    # View action                                                          #
    # ------------------------------------------------------------------ #

    def test_action_view_advance_payment(self):
        """Smart button lists the loans drawn against the PR."""
        pr = self._make_pr()
        ap = self._make_ap(pr)
        result = pr.action_view_advance_payment()
        self.assertEqual(result["res_model"], "advance.payment")
        self.assertEqual(self.env["advance.payment"].search(result["domain"]), ap)
