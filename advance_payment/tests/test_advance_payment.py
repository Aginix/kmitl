import base64

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAdvancePayment(TransactionCase):
    """
    Test suite for the redesigned advance.payment (สัญญายืมเงิน) lifecycle.

    States past `to_approve` need accounting setup (journals, bank export) to
    reach organically, so downstream states are set directly on the record and
    the business logic is exercised in isolation — action_approve /
    return_line.action_approve (which create account.payment) are only tested
    for their guards.
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
                    (6, 0, [cls.env.ref("advance_payment.group_advance_payment_own").id])
                ],
            }
        )
        cls.user2 = Users.create(
            {
                "name": "Borrower B",
                "login": "borrower_b_ap",
                "email": "b@test.local",
                "groups_id": [
                    (6, 0, [cls.env.ref("advance_payment.group_advance_payment_own").id])
                ],
            }
        )
        cls.officer = Users.create(
            {
                "name": "Finance Officer",
                "login": "officer_ap",
                "email": "officer@test.local",
                "groups_id": [
                    (6, 0, [cls.env.ref("advance_payment.group_advance_payment_user").id])
                ],
            }
        )
        cls.viewer = Users.create(
            {
                "name": "AP Viewer",
                "login": "viewer_ap",
                "email": "viewer@test.local",
                "groups_id": [
                    (6, 0, [cls.env.ref("advance_payment.group_advance_payment_viewer").id])
                ],
            }
        )
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )
        cls.banks = {}
        for rec in (cls.manager, cls.user, cls.user2, cls.officer, cls.viewer):
            cls.banks[rec.id] = cls.env["res.partner.bank"].create(
                {"acc_number": "x-%s" % rec.id, "partner_id": rec.partner_id.id}
            )

    def _make(self, requested_by=None, amount=1000, as_user=None):
        requested_by = requested_by or self.manager
        env = self.env(user=as_user) if as_user else self.env
        return env["advance.payment"].create(
            {
                "requested_by": requested_by.id,
                "loan_amount": amount,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "bank_id": self.banks[requested_by.id].id,
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

    def test_submit_report_moves_to_verify_report(self):
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "in_progress",
                "expense_description": "trip",
                "actual_expense_amount": 600,
            }
        )
        ap.action_submit_report()
        self.assertEqual(ap.state, "to_verify_report")

    def test_accept_report_no_leftover_closes(self):
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "to_verify_report",
                "expense_description": "all spent",
                "actual_expense_amount": 1000,
            }
        )
        ap.action_accept_report()
        self.assertEqual(ap.state, "done")

    def test_accept_report_with_leftover_to_reconcile(self):
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "to_verify_report",
                "expense_description": "partial",
                "actual_expense_amount": 700,
            }
        )
        ap.action_accept_report()
        self.assertEqual(ap.state, "to_reconcile")
        self.assertEqual(ap.return_amount, 300)

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
    # Reconcile / auto-close + over-return donation                        #
    # ------------------------------------------------------------------ #

    def test_auto_close_when_returned_covers_leftover(self):
        ap = self._make(amount=1000)
        ap.write({"state": "to_reconcile", "actual_expense_amount": 600})
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 400, "state": "done"}
        )
        ap.invalidate_recordset()
        ap._try_auto_close()
        self.assertEqual(ap.state, "done")

    def test_multiple_partial_returns_close(self):
        ap = self._make(amount=1000)
        ap.write(
            {
                "state": "to_reconcile",
                "actual_expense_amount": 400,
                "return_installment": True,
            }
        )
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 200, "state": "done"}
        )
        ap.invalidate_recordset()
        ap._try_auto_close()
        self.assertEqual(ap.state, "to_reconcile")  # still owes 400
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 400, "state": "done"}
        )
        ap.invalidate_recordset()
        ap._try_auto_close()
        self.assertEqual(ap.state, "done")

    def test_over_return_needs_donation_consent(self):
        ap = self._make(amount=1000)
        ap.write({"state": "to_reconcile", "actual_expense_amount": 200})
        # return_amount 800, returns 850 → excess 50
        self.env["advance.payment.return.line"].create(
            {"agreement_id": ap.id, "amount": 850, "state": "done"}
        )
        ap.invalidate_recordset()
        self.assertEqual(ap.excess_amount, 50)
        ap._try_auto_close()
        self.assertEqual(ap.state, "to_reconcile")  # blocked without consent
        ap.action_confirm_donation()
        self.assertTrue(ap.donate_excess)
        self.assertTrue(ap.donate_consent_uid)
        self.assertEqual(ap.state, "done")  # donation triggers auto-close

    def test_confirm_donation_requires_excess(self):
        ap = self._make(amount=1000)
        ap.write({"state": "to_reconcile"})
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

    def test_requested_by_partner_computed(self):
        ap = self._make(requested_by=self.user)
        self.assertEqual(ap.requested_by_partner_id, self.user.partner_id)

    # ------------------------------------------------------------------ #
    # record rules / ACL                                                   #
    # ------------------------------------------------------------------ #

    def test_own_cannot_read_other_borrower(self):
        ap = self._make(self.user)
        with self.assertRaises(AccessError):
            ap.with_user(self.user2).read(["name"])
        result = self.env["advance.payment"].with_user(self.user2).search(
            [("id", "=", ap.id)]
        )
        self.assertFalse(result)

    def test_viewer_reads_all(self):
        ap = self._make(self.user)
        result = ap.with_user(self.viewer).read(["name"])
        self.assertEqual(result[0]["id"], ap.id)

    def test_viewer_cannot_write_other_records(self):
        ap = self._make(self.user)
        with self.assertRaises(AccessError):
            ap.with_user(self.viewer).write({"loan_reason": "x"})

    def test_viewer_can_create_own(self):
        ap = self._make(self.viewer, as_user=self.viewer)
        self.assertEqual(ap.state, "draft")

    def test_user_tier_writes_other_records(self):
        ap = self._make(self.user)
        ap.with_user(self.officer).write({"loan_reason": "updated by officer"})
        self.assertEqual(ap.loan_reason, "updated by officer")
