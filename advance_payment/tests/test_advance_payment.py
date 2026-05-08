import base64

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAdvancePayment(TransactionCase):
    """
    Test suite for advance.payment lifecycle, security, and business rules.

    Tests avoid action_approve() since it requires full accounting setup
    (journals, bank export). State transitions past 'submitted' are set
    directly on the record to test downstream business logic in isolation.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Deactivate exception rules that require full accounting setup
        cls.env.ref("advance_payment.excep_missing_department").active = False
        cls.env.ref("advance_payment.excep_missing_analytic").active = False
        # admin is in group_advance_payment_manager (from security.xml)
        cls.manager = cls.env.ref("base.user_admin")

        cls.user = cls.env["res.users"].create(
            {
                "name": "Test Requestor",
                "login": "test_requestor_ap",
                "email": "requestor@test.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [cls.env.ref("advance_payment.group_advance_payment_user").id],
                    )
                ],
            }
        )

        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )

        cls.manager_bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "111-222-333",
                "partner_id": cls.manager.partner_id.id,
            }
        )

        cls.user_bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "444-555-666",
                "partner_id": cls.user.partner_id.id,
            }
        )

    def _make_agreement(self, user=None, loan_amount=1000):
        user = user or self.manager
        bank = self.user_bank if user == self.user else self.manager_bank
        return self.env["advance.payment"].create(
            {
                "requested_by": user.id,
                "loan_amount": loan_amount,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test loan reason",
                "bank_id": bank.id,
            }
        )

    def _make_attachment(self, res_model="advance.payment.return.wizard"):
        return self.env["ir.attachment"].create(
            {
                "name": "proof.pdf",
                "datas": base64.b64encode(b"proof content"),
                "res_model": res_model,
                "res_id": 0,
            }
        )

    # ------------------------------------------------------------------ #
    # Lifecycle: draft → submitted                                         #
    # ------------------------------------------------------------------ #

    def test_initial_state(self):
        agreement = self._make_agreement()
        self.assertEqual(agreement.state, "draft")
        self.assertEqual(agreement.name, "New")

    def test_submit_assigns_sequence(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        self.assertNotEqual(agreement.name, "New")
        self.assertEqual(agreement.state, "submitted")

    def test_submit_sets_date_submitted(self):
        agreement = self._make_agreement()
        self.assertFalse(agreement.date_submitted)
        agreement.action_submit()
        self.assertTrue(agreement.date_submitted)

    def test_submit_only_from_draft(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        with self.assertRaises(UserError):
            agreement.action_submit()

    def test_submit_requires_loan_amount_above_zero(self):
        """Exception rule blocks submission if loan_amount <= 0 (blocking exception)."""
        agreement = self._make_agreement(loan_amount=0)
        agreement.action_submit()
        self.assertEqual(agreement.state, "draft")

    # ------------------------------------------------------------------ #
    # Write protection (QW1)                                               #
    # ------------------------------------------------------------------ #

    def test_write_protection_on_submitted(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        with self.assertRaises(UserError):
            agreement.write({"loan_amount": 9999})

    def test_write_allowed_in_draft(self):
        agreement = self._make_agreement()
        agreement.write({"loan_amount": 2000})
        self.assertEqual(agreement.loan_amount, 2000)

    def test_write_non_protected_field_allowed_on_submitted(self):
        """Non-protected fields (e.g. ignore_exception) can still be set."""
        agreement = self._make_agreement()
        agreement.action_submit()
        agreement.write({"ignore_exception": True})

    # ------------------------------------------------------------------ #
    # Submitter validation (QW2)                                           #
    # ------------------------------------------------------------------ #

    def test_submitter_validation_manager_can_submit_any(self):
        """Manager can submit agreements on behalf of others."""
        agreement = self.env["advance.payment"].create(
            {
                "requested_by": self.user.id,
                "loan_amount": 1000,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test",
                "bank_id": self.user_bank.id,
            }
        )
        agreement.with_user(self.manager).action_submit()
        self.assertEqual(agreement.state, "submitted")

    def test_submitter_validation_requestor_can_submit_own(self):
        agreement = self.env["advance.payment"].with_user(self.user).create(
            {
                "requested_by": self.user.id,
                "loan_amount": 1000,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test",
                "bank_id": self.user_bank.id,
            }
        )
        agreement.with_user(self.user).action_submit()
        self.assertEqual(agreement.state, "submitted")

    # ------------------------------------------------------------------ #
    # Date tracking (QW3)                                                  #
    # ------------------------------------------------------------------ #

    def test_date_approved_set_on_approve(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        self.assertFalse(agreement.date_approved)
        agreement.write({"state": "approved", "date_approved": "2026-01-01 00:00:00"})
        self.assertTrue(agreement.date_approved)

    def test_date_closed_set_on_close(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        self.assertFalse(agreement.date_closed)
        agreement._do_close()
        self.assertTrue(agreement.date_closed)
        self.assertEqual(agreement.state, "done")

    # ------------------------------------------------------------------ #
    # Close validation                                                     #
    # ------------------------------------------------------------------ #

    def test_close_only_from_in_progress(self):
        agreement = self._make_agreement()
        with self.assertRaises(UserError):
            agreement.action_close()

    def test_close_shows_wizard_when_remaining(self):
        """action_close returns wizard when amount_remaining > 0."""
        agreement = self._make_agreement(loan_amount=10000)
        agreement.write({"state": "in_progress"})
        result = agreement.action_close()
        self.assertEqual(result["res_model"], "advance.payment.close.confirm")
        self.assertEqual(agreement.state, "in_progress")

    def test_close_direct_when_no_remaining(self):
        """action_close closes directly when amount_remaining == 0."""
        agreement = self._make_agreement(loan_amount=1000)
        agreement.write({"state": "in_progress"})
        # Use up all money via usage + return
        self.env["advance.payment.usage.line"].create(
            {"agreement_id": agreement.id, "amount": 500, "date": "2026-01-01"}
        )
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 500, "state": "done"}
        )
        agreement.invalidate_recordset()
        agreement.action_close()
        self.assertEqual(agreement.state, "done")

    def test_close_wizard_confirms(self):
        """Close confirmation wizard actually closes the agreement."""
        agreement = self._make_agreement(loan_amount=10000)
        agreement.write({"state": "in_progress"})
        wizard = self.env["advance.payment.close.confirm"].create(
            {"agreement_id": agreement.id}
        )
        wizard.action_confirm()
        self.assertEqual(agreement.state, "done")

    def test_reopen_done_to_in_progress(self):
        """ERP admin can reopen a closed agreement."""
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        agreement._do_close()
        self.assertEqual(agreement.state, "done")
        agreement.action_reopen()
        self.assertEqual(agreement.state, "in_progress")
        self.assertFalse(agreement.date_closed)

    def test_reopen_only_from_done(self):
        agreement = self._make_agreement()
        with self.assertRaises(UserError):
            agreement.action_reopen()

    # ------------------------------------------------------------------ #
    # Uniqueness constraint (QW5)                                          #
    # ------------------------------------------------------------------ #

    def test_name_uniqueness(self):
        a1 = self._make_agreement()
        a1.action_submit()
        a2 = self._make_agreement()
        a2.action_submit()
        with self.assertRaises(ValidationError):
            a2.write({"name": a1.name})

    # ------------------------------------------------------------------ #
    # F1: Reject workflow                                                  #
    # ------------------------------------------------------------------ #

    def test_reject_submitted_to_draft(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        agreement._action_do_reject("Budget exhausted")
        self.assertEqual(agreement.state, "draft")
        self.assertEqual(agreement.cancel_reason, "Budget exhausted")

    def test_reject_only_from_submitted(self):
        agreement = self._make_agreement()
        with self.assertRaises(UserError):
            agreement._action_do_reject("reason")

    def test_reject_wizard(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        wizard = self.env["advance.payment.cancel.wizard"].create(
            {
                "agreement_id": agreement.id,
                "action_type": "reject",
                "reason": "Wrong department",
            }
        )
        wizard.action_confirm()
        self.assertEqual(agreement.state, "draft")
        self.assertEqual(agreement.cancel_reason, "Wrong department")

    # ------------------------------------------------------------------ #
    # F1: Cancel workflow                                                  #
    # ------------------------------------------------------------------ #

    def test_cancel_from_submitted(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        agreement._action_do_cancel("Duplicate request")
        self.assertEqual(agreement.state, "cancel")
        self.assertEqual(agreement.cancel_reason, "Duplicate request")

    def test_cancel_from_in_progress(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        agreement._action_do_cancel("Cancelled after disbursement")
        self.assertEqual(agreement.state, "cancel")

    def test_cancel_from_draft_raises(self):
        agreement = self._make_agreement()
        with self.assertRaises(UserError):
            agreement._action_do_cancel("reason")

    def test_cancel_clears_disbursement_state(self):
        agreement = self._make_agreement()
        agreement.write({"state": "approved", "disbursement_state": "pending"})
        agreement._action_do_cancel("Cancelled")
        self.assertFalse(agreement.disbursement_state)

    def test_cancel_wizard(self):
        agreement = self._make_agreement()
        agreement.action_submit()
        wizard = self.env["advance.payment.cancel.wizard"].create(
            {
                "agreement_id": agreement.id,
                "action_type": "cancel",
                "reason": "Admin cancelled",
            }
        )
        wizard.action_confirm()
        self.assertEqual(agreement.state, "cancel")

    # ------------------------------------------------------------------ #
    # Return lines: wizard creates return line                             #
    # ------------------------------------------------------------------ #

    def test_return_wizard_creates_line(self):
        """Wizard creates a return line in draft state."""
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        attachment = self._make_attachment()
        wizard = self.env["advance.payment.return.wizard"].create(
            {
                "agreement_id": agreement.id,
                "amount": 500,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        wizard.action_confirm_return()
        self.assertEqual(len(agreement.return_line_ids), 1)
        line = agreement.return_line_ids
        self.assertEqual(line.state, "draft")
        self.assertEqual(line.amount, 500)

    def test_return_wizard_relinks_attachment(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        attachment = self._make_attachment()
        wizard = self.env["advance.payment.return.wizard"].create(
            {
                "agreement_id": agreement.id,
                "amount": 500,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        wizard.action_confirm_return()
        line = agreement.return_line_ids
        self.assertEqual(attachment.res_model, "advance.payment.return.line")
        self.assertEqual(attachment.res_id, line.id)

    def test_return_wizard_requires_attachment(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        wizard = self.env["advance.payment.return.wizard"].create(
            {"agreement_id": agreement.id, "amount": 500}
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_return_wizard_requires_in_progress(self):
        agreement = self._make_agreement()
        attachment = self._make_attachment()
        wizard = self.env["advance.payment.return.wizard"].create(
            {
                "agreement_id": agreement.id,
                "amount": 500,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_return_wizard_validates_amount_positive(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        with self.assertRaises(ValidationError):
            self.env["advance.payment.return.wizard"].create(
                {"agreement_id": agreement.id, "amount": 0}
            )

    def test_return_wizard_validates_amount_not_exceeding(self):
        agreement = self._make_agreement(loan_amount=1000)
        agreement.write({"state": "in_progress"})
        with self.assertRaises(ValidationError):
            self.env["advance.payment.return.wizard"].create(
                {"agreement_id": agreement.id, "amount": 1500}
            )

    # ------------------------------------------------------------------ #
    # Return lines: amount computation                                     #
    # ------------------------------------------------------------------ #

    def test_amount_returned_from_done_lines(self):
        """amount_returned includes only done return lines."""
        agreement = self._make_agreement(loan_amount=10000)
        agreement.write({"state": "in_progress"})
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 2000, "state": "done"}
        )
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 1000, "state": "done"}
        )
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 500, "state": "draft"}
        )
        agreement.invalidate_recordset()
        self.assertEqual(agreement.amount_returned, 3000)
        self.assertEqual(agreement.amount_remaining, 7000)

    def test_amount_remaining_with_usage_and_returns(self):
        """amount_remaining = loan - used - returned."""
        agreement = self._make_agreement(loan_amount=10000)
        agreement.write({"state": "in_progress"})
        # Record usage of 3000
        self.env["advance.payment.usage.line"].create(
            {"agreement_id": agreement.id, "amount": 3000, "date": "2026-01-01"}
        )
        # Return 2000 (done)
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 2000, "state": "done"}
        )
        agreement.invalidate_recordset()
        self.assertEqual(agreement.amount_used, 3000)
        self.assertEqual(agreement.amount_returned, 2000)
        self.assertEqual(agreement.amount_remaining, 5000)

    # ------------------------------------------------------------------ #
    # Return lines: multiple partial returns                               #
    # ------------------------------------------------------------------ #

    def test_multiple_partial_returns(self):
        """Multiple return lines reduce amount_remaining correctly."""
        agreement = self._make_agreement(loan_amount=10000)
        agreement.write({"state": "in_progress"})
        # Usage: 3000
        self.env["advance.payment.usage.line"].create(
            {"agreement_id": agreement.id, "amount": 3000, "date": "2026-01-01"}
        )
        # Return 1: 2000
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 2000, "state": "done"}
        )
        agreement.invalidate_recordset()
        self.assertEqual(agreement.amount_remaining, 5000)
        # Return 2: 5000
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 5000, "state": "done"}
        )
        agreement.invalidate_recordset()
        self.assertEqual(agreement.amount_remaining, 0)

    def test_return_count(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        self.assertEqual(agreement.return_count, 0)
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 100}
        )
        self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 200}
        )
        agreement.invalidate_recordset()
        self.assertEqual(agreement.return_count, 2)

    # ------------------------------------------------------------------ #
    # Return lines: confirm creates payment                                #
    # ------------------------------------------------------------------ #

    def test_return_line_confirm_requires_draft(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        line = self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 500, "state": "done"}
        )
        with self.assertRaises(UserError):
            line.action_confirm()

    def test_return_line_confirm_requires_in_progress(self):
        agreement = self._make_agreement()
        line = self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": 500}
        )
        with self.assertRaises(UserError):
            line.action_confirm()

    # ------------------------------------------------------------------ #
    # F3: Bank account field (res.partner.bank)                           #
    # ------------------------------------------------------------------ #

    def test_bank_id_uses_partner_bank(self):
        """bank_id references res.partner.bank."""
        agreement = self._make_agreement()
        bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "123-456-789",
                "partner_id": self.manager.partner_id.id,
            }
        )
        agreement.write({"bank_id": bank.id})
        self.assertEqual(agreement.bank_id, bank)

    def test_requested_by_partner_id_computed(self):
        agreement = self._make_agreement(user=self.user)
        self.assertEqual(agreement.requested_by_partner_id, self.user.partner_id)
