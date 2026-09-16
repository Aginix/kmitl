import base64

import psycopg2

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestAdvancePayment(TransactionCase):
    """
    Test suite for the redesigned advance.payment (สัญญายืมเงิน) lifecycle.

    Most states past `to_approve` are set directly on the record rather than
    reached organically, so the business logic can be exercised without a full
    accounting setup.

    `action_create_payment_voucher` and `return_line.action_approve` are the
    two places that create an `account.payment`, and both are run for real,
    not just guard-tested — leaving them guard-only is how a call to a
    non-existent `account.payment.action_submit` once survived in both of
    them until somebody clicked อนุมัติ (ADR-0006). `action_approve` itself no
    longer creates a payment: issuing the voucher is a separate, later act.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The dimension rule needs master data these tests do not set up. Look
        # it up by content rather than by xml id: it lives in
        # advance_payment_budget now, but a database upgraded from before the
        # split can still carry the pre-split copy under
        # `advance_payment.excep_missing_analytic`, and that one reads fields
        # this module no longer defines.
        cls.env["exception.rule"].search(
            [
                ("model", "=", "advance.payment"),
                "|",
                ("code", "ilike", "analytic_id"),
                ("domain", "ilike", "department_id"),
            ]
        ).active = False

        cls.manager = cls.env.ref("base.user_admin")  # in manager group
        Users = cls.env["res.users"]
        cls.user = Users.create(
            {
                "name": "Borrower A",
                "login": "borrower_a_ap",
                "email": "a@test.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [cls.env.ref("advance_payment.group_advance_payment_own_only").id],
                    )
                ],
            }
        )
        cls.user2 = Users.create(
            {
                "name": "Borrower B",
                "login": "borrower_b_ap",
                "email": "b@test.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [cls.env.ref("advance_payment.group_advance_payment_own_only").id],
                    )
                ],
            }
        )
        cls.staff = Users.create(
            {
                "name": "Data Entry Staff",
                "login": "staff_ap",
                "email": "staff@test.local",
                "groups_id": [
                    (6, 0, [cls.env.ref("advance_payment.group_advance_payment_user").id])
                ],
            }
        )
        cls.officer = Users.create(
            {
                "name": "Loan Officer",
                "login": "officer_ap",
                "email": "officer@test.local",
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
        cls.officer2 = Users.create(
            {
                "name": "Other Loan Officer",
                "login": "officer2_ap",
                "email": "officer2@test.local",
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
        cls.approver = Users.create(
            {
                "name": "Loan Approver",
                "login": "approver_ap",
                "email": "approver@test.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref(
                                "advance_payment.group_advance_payment_loan_approver"
                            ).id
                        ],
                    )
                ],
            }
        )
        cls.approver2 = Users.create(
            {
                "name": "Other Loan Approver",
                "login": "approver2_ap",
                "email": "approver2@test.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref(
                                "advance_payment.group_advance_payment_loan_approver"
                            ).id
                        ],
                    )
                ],
            }
        )
        cls.loan_officer = Users.create(
            {
                "name": "Loan Officer",
                "login": "loan_officer_ap",
                "email": "loan_officer@test.local",
                "groups_id": [
                    (6, 0, [cls.env.ref("advance_payment.group_advance_payment_loan_officer").id])
                ],
            }
        )
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )
        # Give every acting user a linked hr.employee — the borrower field is
        # now employee_id (ADR-0014). Passing user_id at create makes core
        # _sync_user mirror work_contact_id = user.partner_id, so the bank
        # fixtures below (keyed on user.partner_id) still resolve. cls.manager
        # (base.user_admin) already has one — hr's own data.xml seeds
        # hr.employee_admin with user_id=base.user_admin on every database, so
        # creating a second one here would violate hr_employee_user_uniq.
        Employee = cls.env["hr.employee"]
        cls.emp = {}
        for u in (cls.manager, cls.user, cls.user2, cls.staff, cls.officer):
            existing = Employee.search([("user_id", "=", u.id)], limit=1)
            cls.emp[u.id] = existing or Employee.create(
                {"name": u.name, "user_id": u.id}
            )
        cls.banks = {}
        for rec in (cls.manager, cls.user, cls.user2, cls.staff, cls.officer):
            cls.banks[rec.id] = cls.env["res.partner.bank"].create(
                {"acc_number": "x-%s" % rec.id, "partner_id": rec.partner_id.id}
            )

    def _make(self, requested_by=None, amount=1000, as_user=None, loan_verifier_id=None):
        requested_by = requested_by or self.manager
        verifier = loan_verifier_id if loan_verifier_id is not None else self.officer
        env = self.env(user=as_user) if as_user else self.env
        return env["advance.payment"].create(
            {
                "employee_id": self.emp[requested_by.id].id,
                "loan_amount": amount,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "bank_id": self.banks[requested_by.id].id,
                "loan_verifier_id": verifier.id,
            }
        )

    def _attachment(self, model="advance.payment.return.wizard"):
        return self.env["ir.attachment"].create(
            {
                "name": "proof.pdf",
                "datas": base64.b64encode(b"x"),
                "res_model": model,
                "res_id": 0,
            }
        )

    # ------------------------------------------------------------------ #
    # draft → to_verify                                                    #
    # ------------------------------------------------------------------ #

    def test_initial_state(self):
        ap = self._make()
        self.assertEqual(ap.state, "draft")
        self.assertEqual(ap.name, "New")

    def test_submit_moves_to_verify_and_numbers(self):
        ap = self._make()
        ap.action_submit()
        self.assertEqual(ap.state, "to_verify")
        self.assertNotEqual(ap.name, "New")
        self.assertTrue(ap.date_submitted)

    def test_submit_only_from_draft(self):
        ap = self._make()
        ap.action_submit()
        with self.assertRaises(UserError):
            ap.action_submit()

    def test_submit_blocked_by_zero_amount(self):
        """Blocking exception rule keeps a zero-amount request in draft."""
        ap = self._make(amount=0)
        ap.action_submit()
        self.assertEqual(ap.state, "draft")

    # ------------------------------------------------------------------ #
    # Creator-only (ADR-0005)                                              #
    # ------------------------------------------------------------------ #

    def test_creator_can_submit_own(self):
        ap = self._make(requested_by=self.user, as_user=self.user)
        ap.with_user(self.user).action_submit()
        self.assertEqual(ap.state, "to_verify")

    def test_non_creator_cannot_submit(self):
        ap = self._make(requested_by=self.user)
        with self.assertRaises(UserError):
            ap.with_user(self.user2).action_submit()

    def test_admin_can_submit_on_behalf(self):
        ap = self._make(requested_by=self.user)
        ap.with_user(self.manager).action_submit()
        self.assertEqual(ap.state, "to_verify")

    def test_create_on_behalf_blocked_for_non_admin(self):
        with self.assertRaises(ValidationError):
            self._make(requested_by=self.user2, as_user=self.user)

    # ------------------------------------------------------------------ #
    # Role tiers: own-only / user / loan officer (ADR-0010)                #
    # ------------------------------------------------------------------ #

    def test_user_tier_can_draft_on_behalf(self):
        ap = self._make(requested_by=self.user2, as_user=self.staff)
        self.assertEqual(ap.employee_id, self.emp[self.user2.id])
        self.assertEqual(ap.create_uid, self.staff)
        self.assertEqual(ap.user_id, self.staff)

    def test_user_tier_can_pick_borrower_in_form(self):
        """The UI gate must match _check_creator_only, not base.group_system.

        can_draft_on_behalf has no field dependency (it only reads
        self.env.user), so Odoo's field cache — keyed by record id, not by
        uid — would otherwise serve the first with_user()'s stale value to
        the next; invalidate between reads to force a fresh compute.
        """
        ap = self._make(requested_by=self.user2, as_user=self.staff)
        self.assertTrue(ap.with_user(self.staff).can_draft_on_behalf)
        ap.invalidate_recordset()
        self.assertTrue(ap.with_user(self.manager).can_draft_on_behalf)
        ap.invalidate_recordset()
        self.assertFalse(ap.with_user(self.user2).can_draft_on_behalf)

    def test_user_tier_cannot_submit_drafted_on_behalf(self):
        ap = self._make(requested_by=self.user2, as_user=self.staff)
        with self.assertRaises(UserError):
            ap.with_user(self.staff).action_submit()
        ap.with_user(self.user2).action_submit()
        self.assertEqual(ap.state, "to_verify")

    def test_loan_officer_can_verify_and_close(self):
        ap = self._make(amount=1000)
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        self.assertEqual(ap.state, "to_approve")
        ap.write(
            {
                "state": "in_progress",
                "expense_description": "all spent",
                "actual_expense_amount": 1000,
            }
        )
        ap.with_user(self.officer).action_close()
        self.assertEqual(ap.state, "done")

    def test_own_only_sees_only_own_records(self):
        ap_own = self._make(requested_by=self.user, as_user=self.user)
        ap_other = self._make(requested_by=self.user2)
        visible = (
            self.env["advance.payment"]
            .with_user(self.user)
            .search([("id", "in", (ap_own | ap_other).ids)])
        )
        self.assertEqual(visible, ap_own)

    # ------------------------------------------------------------------ #
    # One active agreement per borrower (ADR-0001)                         #
    # ------------------------------------------------------------------ #

    def test_one_active_blocks_second_submit(self):
        a1 = self._make(requested_by=self.user)
        a1.action_submit()
        a2 = self._make(requested_by=self.user)
        with self.assertRaises(UserError):
            a2.action_submit()

    def test_done_agreement_does_not_block(self):
        a1 = self._make(requested_by=self.user)
        a1.action_submit()
        a1.write({"state": "done"})
        a2 = self._make(requested_by=self.user)
        a2.action_submit()
        self.assertEqual(a2.state, "to_verify")

    def test_other_borrower_does_not_block(self):
        a1 = self._make(requested_by=self.user)
        a1.action_submit()
        a2 = self._make(requested_by=self.user2)
        a2.action_submit()
        self.assertEqual(a2.state, "to_verify")

    # ------------------------------------------------------------------ #
    # verify / approve guards                                              #
    # ------------------------------------------------------------------ #

    def test_verify_moves_to_approve(self):
        ap = self._make()
        ap.action_submit()
        ap.action_verify()
        self.assertEqual(ap.state, "to_approve")

    def test_verify_only_from_to_verify(self):
        ap = self._make()
        with self.assertRaises(UserError):
            ap.action_verify()

    def test_approve_only_from_to_approve(self):
        ap = self._make()
        ap.action_submit()
        with self.assertRaises(UserError):
            ap.action_approve()

    def test_approve_moves_to_waiting_transfer_without_payment(self):
        """Approval hands the request to the loan officer; issuing the
        voucher is a separate, later act (see the payment-voucher tests
        below) — action_approve itself must not create a payment."""
        ap = self._make()
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        ap.action_approve()
        self.assertEqual(ap.state, "waiting_transfer")
        self.assertEqual(ap.disbursement_state, "pending")
        self.assertTrue(ap.date_approved)
        self.assertEqual(ap.payment_count, 0)

    # ------------------------------------------------------------------ #
    # Payment voucher issuance (loan officer)                              #
    # ------------------------------------------------------------------ #

    def test_loan_officer_creates_payment_voucher(self):
        ap = self._make(requested_by=self.user, amount=1000)
        ap.write({"state": "waiting_transfer", "disbursement_state": "pending"})
        ap.with_user(self.officer).action_create_payment_voucher()
        self.assertEqual(ap.payment_count, 1)
        payment = ap.payment_ids
        self.assertEqual(payment.state, "draft")
        self.assertEqual(payment.finance_state, "draft")
        self.assertEqual(
            payment.kmitl_payment_type_id,
            self.env.ref("advance_payment.payment_type_advance_payment_outbound"),
        )
        self.assertEqual(payment.partner_id, ap.partner_id)
        self.assertEqual(payment.partner_bank_id, ap.bank_id)
        self.assertEqual(payment.amount, 1000)
        with self.assertRaises(UserError):
            ap.with_user(self.officer).action_create_payment_voucher()

    def test_create_payment_voucher_requires_loan_officer(self):
        ap = self._make(requested_by=self.user)
        ap.write({"state": "waiting_transfer"})
        with self.assertRaises(AccessError):
            ap.with_user(self.staff).action_create_payment_voucher()

    def test_create_payment_voucher_only_from_waiting_transfer(self):
        ap = self._make()
        with self.assertRaises(UserError):
            ap.with_user(self.officer).action_create_payment_voucher()

    def test_cancel_after_approve_voids_the_voucher(self):
        ap = self._make()
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        ap.action_approve()
        ap.with_user(self.officer).action_create_payment_voucher()
        ap._action_do_cancel("stopped")
        self.assertEqual(ap.state, "cancel")
        self.assertEqual(ap.payment_ids.state, "cancel")
        self.assertFalse(ap.disbursement_state)

    # ------------------------------------------------------------------ #
    # Loan officer assignment (ADR-0013)                                   #
    # ------------------------------------------------------------------ #

    def test_loan_verifier_id_required(self):
        with self.assertRaises(psycopg2.IntegrityError):
            with mute_logger("odoo.sql_db"), self.cr.savepoint():
                self._make(loan_verifier_id=self.env["res.users"])

    def test_assigned_officer_can_verify(self):
        ap = self._make()
        ap.action_submit()
        self.assertTrue(ap.with_user(self.officer).can_verify)
        ap.with_user(self.officer).action_verify()
        self.assertEqual(ap.state, "to_approve")

    def test_other_officer_cannot_verify(self):
        ap = self._make()
        ap.action_submit()
        self.assertFalse(ap.with_user(self.officer2).can_verify)
        with self.assertRaises(UserError):
            ap.with_user(self.officer2).action_verify()

    def test_admin_can_verify_any_assignment(self):
        ap = self._make()
        ap.action_submit()
        ap.with_user(self.manager).action_verify()
        self.assertEqual(ap.state, "to_approve")

    def test_submit_schedules_verify_activity(self):
        ap = self._make()
        ap.action_submit()
        activity = ap.activity_ids.filtered(
            lambda a: a.user_id == self.officer
        )
        self.assertTrue(activity)

    # ------------------------------------------------------------------ #
    # Verify To-Do lifecycle + defaults (ADR-0015)                         #
    # ------------------------------------------------------------------ #

    def test_verify_marks_activity_done(self):
        ap = self._make()
        ap.action_submit()
        self.assertTrue(ap._workflow_activities("to_verify"))
        ap.with_user(self.officer).action_verify()
        # _action_done unlinks the activity and leaves an mt_activities
        # message as the done trail — assert both halves.
        self.assertFalse(ap._workflow_activities("to_verify"))
        self.assertTrue(
            ap.message_ids.filtered(
                lambda m: m.subtype_id
                == self.env.ref("mail.mt_activities")
            )
        )

    def test_reset_to_draft_drops_activity(self):
        ap = self._make()
        ap.action_submit()
        self.assertTrue(ap._workflow_activities("to_verify"))
        ap.with_user(self.officer).action_reset_to_draft()
        self.assertFalse(ap._workflow_activities("to_verify"))

    def test_recall_drops_activity(self):
        ap = self._make(requested_by=self.user)
        ap.with_user(self.user).action_submit()
        self.assertTrue(ap._workflow_activities("to_verify"))
        ap.with_user(self.user).action_recall()
        self.assertFalse(ap._workflow_activities("to_verify"))

    def test_cancel_drops_activity(self):
        ap = self._make()
        ap.action_submit()
        self.assertTrue(ap._workflow_activities("to_verify"))
        ap._action_do_cancel("dup")
        self.assertFalse(ap._workflow_activities("to_verify"))

    def test_default_loan_verifier_from_settings(self):
        """With two officers the sole-officer fallback is ambiguous, so the
        configured one is what makes the required field defaultable."""
        self.assertFalse(self.env["advance.payment"]._default_loan_verifier_id())
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.default_loan_verifier_id", str(self.officer2.id)
        )
        self.assertEqual(
            self.env["advance.payment"]._default_loan_verifier_id(), self.officer2.id
        )

    def test_default_loan_verifier_ignores_stale_setting(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.default_loan_verifier_id", str(self.user.id)
        )  # not a loan officer
        self.assertFalse(self.env["advance.payment"]._default_loan_verifier_id())

    def test_bank_auto_filled_on_borrower_change(self):
        ap = self._make(requested_by=self.user)
        ap.employee_id = self.emp[self.user2.id]
        ap._onchange_employee_id()
        self.assertEqual(ap.bank_id, self.banks[self.user2.id])

    def test_manager_cancel_drops_officer_todo(self):
        """mail_activity_rule_user limits write/unlink to the to-do's user_id
        or create_uid — here the officer and the borrower. A manager is
        neither, so this only works because the helper sudo()s."""
        ap = self._make(requested_by=self.user)
        ap.with_user(self.user).action_submit()
        self.assertTrue(ap._workflow_activities("to_verify"))
        ap.with_user(self.manager)._action_do_cancel("dup")
        self.assertFalse(ap._workflow_activities("to_verify"))

    # ------------------------------------------------------------------ #
    # Approver assignment + approve To-Do (ADR-0016)                       #
    # ------------------------------------------------------------------ #

    def test_default_approver_is_admin_when_unset(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.default_approver_id", ""
        )
        self.assertEqual(
            self.env["advance.payment"]._default_approver_id(),
            self.env.ref("base.user_admin").id,
        )

    def test_default_approver_ignores_non_approver(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment.default_approver_id", str(self.user.id)
        )  # own-only tier, not in the loan-approver group
        self.assertEqual(
            self.env["advance.payment"]._default_approver_id(),
            self.env.ref("base.user_admin").id,
        )

    def test_new_agreement_gets_approver(self):
        self.assertTrue(self._make().approver_id)

    def test_verify_schedules_approve_activity(self):
        ap = self._make()
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        todo = ap._workflow_activities("to_approve")
        self.assertTrue(todo)
        self.assertEqual(todo.user_id, ap.approver_id)

    def test_cancel_from_to_approve_drops_approve_activity(self):
        ap = self._make()
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        self.assertTrue(ap._workflow_activities("to_approve"))
        ap._action_do_cancel("dup")
        self.assertFalse(ap._workflow_activities())

    # ------------------------------------------------------------------ #
    # Approval narrowed to the named approver (ADR-0017)                   #
    # ------------------------------------------------------------------ #

    def test_assigned_approver_can_approve(self):
        ap = self._make()
        ap.approver_id = self.approver.id
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        self.assertTrue(ap.with_user(self.approver).can_approve)
        ap.with_user(self.approver).action_approve()
        self.assertEqual(ap.state, "waiting_transfer")

    def test_other_approver_cannot_approve(self):
        ap = self._make()
        ap.approver_id = self.approver.id
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        self.assertFalse(ap.with_user(self.approver2).can_approve)
        with self.assertRaises(UserError):
            ap.with_user(self.approver2).action_approve()

    def test_admin_can_approve_any_assignment(self):
        ap = self._make()
        ap.approver_id = self.approver.id
        ap.action_submit()
        ap.with_user(self.officer).action_verify()
        ap.with_user(self.manager).action_approve()
        self.assertEqual(ap.state, "waiting_transfer")

    # ------------------------------------------------------------------ #
    # Recall / reset                                                       #
    # ------------------------------------------------------------------ #

    def test_recall_from_to_verify_keeps_number(self):
        ap = self._make(requested_by=self.user)
        ap.with_user(self.user).action_submit()
        number = ap.name
        ap.with_user(self.user).action_recall()
        self.assertEqual(ap.state, "draft")
        self.assertEqual(ap.name, number)

    def test_recall_from_to_approve(self):
        ap = self._make(requested_by=self.user)
        ap.with_user(self.user).action_submit()
        ap.action_verify()
        ap.with_user(self.user).action_recall()
        self.assertEqual(ap.state, "draft")

    def test_recall_only_borrower(self):
        ap = self._make(requested_by=self.user)
        ap.action_submit()
        with self.assertRaises(UserError):
            ap.with_user(self.user2).action_recall()

    def test_recall_not_after_approval(self):
        ap = self._make(requested_by=self.user)
        ap.write({"state": "waiting_transfer"})
        with self.assertRaises(UserError):
            ap.with_user(self.user).action_recall()

    def test_officer_reset_to_draft(self):
        ap = self._make()
        ap.action_submit()
        ap.with_user(self.officer).action_reset_to_draft()
        self.assertEqual(ap.state, "draft")

    # ------------------------------------------------------------------ #
    # Effective date + contract number (action_start)                     #
    # ------------------------------------------------------------------ #

    def test_start_sets_effective_date_and_contract(self):
        ap = self._make()
        ap.write({"state": "waiting_transfer"})
        ap.action_start()
        self.assertEqual(ap.state, "in_progress")
        self.assertTrue(ap.effective_date)
        self.assertTrue(ap.contract_number)
        self.assertNotEqual(ap.contract_number, ap.name)

    # ------------------------------------------------------------------ #
    # Expense report → accept                                              #
    # ------------------------------------------------------------------ #

    def test_submit_report_requires_expense(self):
        ap = self._make()
        ap.write({"state": "in_progress"})
        with self.assertRaises(UserError):
            ap.action_submit_report()

    def test_submit_report_stays_in_progress(self):
        """Reporting the actual expense no longer gates behind a review
        state — the agreement stays in_progress and the borrower is free to
        return any leftover right away."""
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "in_progress",
                "expense_description": "trip",
                "actual_expense_amount": 600,
            }
        )
        ap.action_submit_report()
        self.assertEqual(ap.state, "in_progress")
        self.assertEqual(ap.return_amount, 400)

    def test_close_with_no_leftover(self):
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "in_progress",
                "expense_description": "all spent",
                "actual_expense_amount": 1000,
            }
        )
        ap.with_user(self.officer).action_close()
        self.assertEqual(ap.state, "done")

    def test_close_blocked_with_leftover(self):
        """Closing is a deliberate loan-officer action — it never happens
        automatically, and it refuses while a balance is still owed."""
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "in_progress",
                "expense_description": "partial",
                "actual_expense_amount": 700,
            }
        )
        self.assertEqual(ap.return_amount, 300)
        with self.assertRaises(UserError):
            ap.with_user(self.officer).action_close()

    # ------------------------------------------------------------------ #
    # Amounts                                                              #
    # ------------------------------------------------------------------ #

    def test_amounts(self):
        ap = self._make(amount=10000)
        ap.write({"state": "in_progress", "actual_expense_amount": 3000})
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 2000, "state": "done"}
        )
        ap.invalidate_recordset()
        self.assertEqual(ap.actual_expense_amount, 3000)
        self.assertEqual(ap.amount_returned, 2000)
        self.assertEqual(ap.amount_remaining, 5000)
        self.assertEqual(ap.return_amount, 7000)
        self.assertEqual(ap.excess_amount, 0)

    # ------------------------------------------------------------------ #
    # Close (loan-officer only, never automatic) + over-return donation    #
    # ------------------------------------------------------------------ #

    def test_close_when_returned_covers_leftover(self):
        ap = self._make(amount=1000)
        ap.write({"state": "in_progress", "actual_expense_amount": 600})
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 400, "state": "done"}
        )
        ap.invalidate_recordset()
        ap.with_user(self.officer).action_close()
        self.assertEqual(ap.state, "done")

    def test_return_line_approve_creates_inbound_voucher(self):
        """The inbound half of the money path, run for real.

        It carried the same call to a non-existent
        `account.payment.action_submit` as the outbound one, and was likewise
        only ever tested for its guards.
        """
        ap = self._make(amount=1000)
        ap.write({"state": "in_progress", "actual_expense_amount": 600})
        line = self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 400, "state": "pending_review"}
        )
        line.with_user(self.officer).action_approve()
        self.assertEqual(line.state, "done")
        self.assertTrue(line.payment_id)
        self.assertEqual(line.payment_id.state, "draft")
        self.assertEqual(line.payment_id.finance_state, "draft")
        self.assertEqual(line.payment_id.partner_id, ap.partner_id)
        self.assertEqual(line.payment_id.payment_type, "inbound")
        # Fully returned, but closing is never automatic — the agreement
        # stays open until the loan officer presses it themselves.
        self.assertEqual(ap.state, "in_progress")
        ap.with_user(self.officer).action_close()
        self.assertEqual(ap.state, "done")

    def test_multiple_partial_returns_close(self):
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "in_progress",
                "actual_expense_amount": 400,
                "return_installment": True,
            }
        )
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 200, "state": "done"}
        )
        ap.invalidate_recordset()
        with self.assertRaises(UserError):
            ap.with_user(self.officer).action_close()  # still owes 400
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 400, "state": "done"}
        )
        ap.invalidate_recordset()
        ap.with_user(self.officer).action_close()
        self.assertEqual(ap.state, "done")

    def test_over_return_needs_donation_consent(self):
        ap = self._make(amount=1000)
        ap.write({"state": "in_progress", "actual_expense_amount": 200})
        # return_amount 800, returns 850 → excess 50
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 850, "state": "done"}
        )
        ap.invalidate_recordset()
        self.assertEqual(ap.excess_amount, 50)
        with self.assertRaises(UserError):
            ap.with_user(self.officer).action_close()  # blocked without consent
        ap.action_confirm_donation()
        self.assertTrue(ap.donate_excess)
        self.assertTrue(ap.donate_consent_uid)
        self.assertEqual(ap.state, "in_progress")  # donation alone doesn't close it
        ap.with_user(self.officer).action_close()
        self.assertEqual(ap.state, "done")

    def test_confirm_donation_requires_excess(self):
        ap = self._make(amount=1000)
        ap.write({"state": "in_progress"})
        with self.assertRaises(UserError):
            ap.action_confirm_donation()

    # ------------------------------------------------------------------ #
    # Edit rights (ADR-0001/0005)                                          #
    # ------------------------------------------------------------------ #

    def test_material_field_locked_for_borrower_after_submit(self):
        ap = self._make(requested_by=self.user)
        ap.with_user(self.user).action_submit()
        with self.assertRaises(UserError):
            ap.with_user(self.user).write({"loan_amount": 5000})

    def test_officer_can_edit_material_in_to_verify(self):
        ap = self._make(requested_by=self.user)
        ap.with_user(self.user).action_submit()
        ap.with_user(self.officer).write({"loan_amount": 4200})
        self.assertEqual(ap.loan_amount, 4200)

    def test_loan_reason_editable_in_to_verify(self):
        ap = self._make(requested_by=self.user)
        ap.with_user(self.user).action_submit()
        ap.with_user(self.user).write({"loan_reason": "updated"})
        self.assertEqual(ap.loan_reason, "updated")

    def test_bank_editable_by_officer_until_transfer(self):
        ap = self._make(requested_by=self.user)
        ap.write({"state": "waiting_transfer"})
        new_bank = self.env["res.partner.bank"].create(
            {"acc_number": "new-1", "partner_id": self.user.partner_id.id}
        )
        ap.with_user(self.officer).write({"bank_id": new_bank.id})
        self.assertEqual(ap.bank_id, new_bank)

    def test_write_allowed_in_draft(self):
        ap = self._make()
        ap.write({"loan_amount": 2000})
        self.assertEqual(ap.loan_amount, 2000)

    # ------------------------------------------------------------------ #
    # Cancel                                                               #
    # ------------------------------------------------------------------ #

    def test_cancel_from_in_progress(self):
        ap = self._make()
        ap.write({"state": "in_progress"})
        ap._action_do_cancel("stopped")
        self.assertEqual(ap.state, "cancel")
        self.assertEqual(ap.cancel_reason, "stopped")

    def test_cancel_from_draft_raises(self):
        ap = self._make()
        with self.assertRaises(UserError):
            ap._action_do_cancel("x")

    def test_cancel_wizard(self):
        ap = self._make()
        ap.action_submit()
        wiz = self.env["advance.payment.cancel.wizard"].create(
            {"agreement_id": ap.id, "action_type": "cancel", "reason": "dup"}
        )
        wiz.action_confirm()
        self.assertEqual(ap.state, "cancel")

    def test_reset_cancel_to_draft_before_disbursement(self):
        ap = self._make()
        ap.action_submit()
        ap._action_do_cancel("dup")
        ap.action_reset_cancel_to_draft()
        self.assertEqual(ap.state, "draft")
        self.assertFalse(ap.cancel_reason)
        self.assertFalse(ap.date_submitted)

    def test_reset_cancel_to_draft_blocked_after_disbursement(self):
        ap = self._make()
        ap.write({"state": "in_progress", "effective_date": fields.Date.today()})
        ap._action_do_cancel("stopped")
        with self.assertRaises(UserError):
            ap.action_reset_cancel_to_draft()

    # ------------------------------------------------------------------ #
    # Delete requires cancel first (ADR-0018)                              #
    # ------------------------------------------------------------------ #

    def test_delete_blocked_before_cancel(self):
        ap = self._make(requested_by=self.user, as_user=self.user)
        with self.assertRaises(UserError):
            ap.with_user(self.user).unlink()

    def test_own_only_can_delete_own_cancelled_draft(self):
        ap = self._make(requested_by=self.user, as_user=self.user)
        ap.with_user(self.user).button_cancel()
        ap_id = ap.id
        ap.with_user(self.user).unlink()
        self.assertFalse(self.env["advance.payment"].search([("id", "=", ap_id)]))

    def test_own_only_can_delete_after_cancel_from_to_verify(self):
        ap = self._make(requested_by=self.user, as_user=self.user)
        ap.with_user(self.user).action_submit()
        ap.with_user(self.user)._action_do_cancel("dup")
        self.assertEqual(ap.state, "cancel")
        ap.with_user(self.user).unlink()
        self.assertFalse(ap.exists())

    def test_admin_can_delete_without_cancel(self):
        ap = self._make()
        ap.with_user(self.manager).unlink()
        self.assertFalse(ap.exists())

    # ------------------------------------------------------------------ #
    # Uniqueness                                                           #
    # ------------------------------------------------------------------ #

    def test_name_uniqueness(self):
        a1 = self._make()
        a1.action_submit()
        a2 = self._make(requested_by=self.user)
        a2.action_submit()
        with self.assertRaises(ValidationError):
            a2.write({"name": a1.name})

    def test_partner_id_computed_from_work_contact(self):
        ap = self._make(requested_by=self.user)
        self.assertEqual(ap.partner_id, self.user.partner_id)

    # ------------------------------------------------------------------ #
    # Employee without a user account (decision 3)                         #
    # ------------------------------------------------------------------ #

    def test_employee_without_user_can_draft_but_not_submit(self):
        employee = self.env["hr.employee"].create({"name": "No User Employee"})
        ap = self.env["advance.payment"].create(
            {
                "employee_id": employee.id,
                "loan_amount": 1000,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "loan_verifier_id": self.officer.id,
                # No work_contact_id on a bare employee to auto-fill bank_id
                # from (ADR-0015) — set it explicitly, unrelated to what this
                # test actually exercises (submit permission).
                "bank_id": self.banks[self.manager.id].id,
            }
        )
        self.assertEqual(ap.state, "draft")
        with self.assertRaises(UserError):
            ap.with_user(self.staff).action_submit()
        ap.with_user(self.manager).action_submit()
        self.assertEqual(ap.state, "to_verify")

    # ------------------------------------------------------------------ #
    # Own-only rule ORs in the drafter (ADR-0014)                          #
    # ------------------------------------------------------------------ #

    def test_own_only_rule_ors_drafter(self):
        ap = self._make(requested_by=self.user2, as_user=self.staff)
        # Drop staff from the `user` tier, leaving only own-only.
        self.env.ref("advance_payment.group_advance_payment_user").write(
            {"users": [(3, self.staff.id)]}
        )
        self.env.ref("advance_payment.group_advance_payment_own_only").write(
            {"users": [(4, self.staff.id)]}
        )
        visible_to_staff = (
            self.env["advance.payment"].with_user(self.staff).search([("id", "=", ap.id)])
        )
        self.assertEqual(visible_to_staff, ap)
        visible_to_user2 = (
            self.env["advance.payment"].with_user(self.user2).search([("id", "=", ap.id)])
        )
        self.assertEqual(visible_to_user2, ap)
        visible_to_user = (
            self.env["advance.payment"].with_user(self.user).search([("id", "=", ap.id)])
        )
        self.assertFalse(visible_to_user)

    # ------------------------------------------------------------------ #
    # Strict own-only mode (ADR-0014)                                      #
    # ------------------------------------------------------------------ #

    def test_strict_mode_blocks_draft_on_behalf_except_admin(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("advance_payment.strict_own_only", "True")
        try:
            AP = self.env["advance.payment"]
            self.assertFalse(AP.with_user(self.staff)._can_draft_on_behalf())
            self.assertTrue(AP.with_user(self.manager)._can_draft_on_behalf())
            with self.assertRaises(ValidationError):
                self._make(requested_by=self.user2, as_user=self.staff)
        finally:
            params.set_param("advance_payment.strict_own_only", "False")
        # Strict mode off again → draft-on-behalf works as before.
        self._make(requested_by=self.user2, as_user=self.staff)

    # ------------------------------------------------------------------ #
    # can_edit_drafter (ADR-0014)                                          #
    # ------------------------------------------------------------------ #

    def test_can_edit_drafter_manager_only(self):
        # can_edit_drafter has no field dependency — invalidate between
        # with_user() reads so the field cache (keyed by record id, not uid)
        # doesn't serve a stale value from the previous user's compute.
        ap = self._make()
        self.assertTrue(ap.with_user(self.manager).can_edit_drafter)
        ap.invalidate_recordset()
        self.assertFalse(ap.with_user(self.staff).can_edit_drafter)
        ap.invalidate_recordset()
        self.assertFalse(ap.with_user(self.officer).can_edit_drafter)
