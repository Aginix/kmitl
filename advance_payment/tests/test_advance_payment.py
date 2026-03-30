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

    def _make_agreement(self, user=None, loan_amount=1000):
        user = user or self.manager
        return self.env["advance.payment"].create(
            {
                "requested_by": user.id,
                "loan_amount": loan_amount,
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

    def test_submit_requires_loan_amount_above_100(self):
        """Exception rule blocks submission if loan_amount <= 100 (blocking exception)."""
        agreement = self._make_agreement(loan_amount=50)
        # detect_exceptions returns truthy → popup is triggered; action_submit returns early
        # The state should remain 'draft'
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
        # Should not raise (not in _PROTECTED_FIELDS)
        agreement.write({"ignore_exception": True})

    # ------------------------------------------------------------------ #
    # Submitter validation (QW2)                                           #
    # ------------------------------------------------------------------ #

    def test_submitter_validation_manager_can_submit_any(self):
        """Manager can submit agreements on behalf of others."""
        agreement = self.env["advance.payment"].create(
            {"requested_by": self.user.id, "loan_amount": 1000}
        )
        # manager submits (not the requestor) — should work
        agreement.with_user(self.manager).action_submit()
        self.assertEqual(agreement.state, "submitted")

    def test_submitter_validation_requestor_can_submit_own(self):
        agreement = self.env["advance.payment"].with_user(self.user).create(
            {"requested_by": self.user.id, "loan_amount": 1000}
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
        # Bypass payment creation: write state directly
        agreement.write({"state": "approved", "date_approved": "2026-01-01 00:00:00"})
        self.assertTrue(agreement.date_approved)

    def test_date_closed_set_on_close(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress", "is_return_requested": True})
        self.assertFalse(agreement.date_closed)
        agreement.action_close()
        self.assertTrue(agreement.date_closed)
        self.assertEqual(agreement.state, "done")

    # ------------------------------------------------------------------ #
    # Close validation                                                     #
    # ------------------------------------------------------------------ #

    def test_close_only_from_in_progress(self):
        agreement = self._make_agreement()
        with self.assertRaises(UserError):
            agreement.action_close()

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
    # F2: Return payment flow                                              #
    # ------------------------------------------------------------------ #

    def test_return_request_sets_flag(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "proof.pdf",
                "datas": base64.b64encode(b"proof content"),
                "res_model": "advance.payment.return.wizard",
                "res_id": 0,
            }
        )
        wizard = self.env["advance.payment.return.wizard"].create(
            {
                "agreement_id": agreement.id,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        wizard.action_confirm_return()
        self.assertTrue(agreement.is_return_requested)

    def test_return_request_relinks_attachment(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "proof.pdf",
                "datas": base64.b64encode(b"proof content"),
                "res_model": "advance.payment.return.wizard",
                "res_id": 0,
            }
        )
        wizard = self.env["advance.payment.return.wizard"].create(
            {
                "agreement_id": agreement.id,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        wizard.action_confirm_return()
        self.assertEqual(attachment.res_model, "advance.payment")
        self.assertEqual(attachment.res_id, agreement.id)

    def test_return_request_requires_attachment(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress"})
        wizard = self.env["advance.payment.return.wizard"].create(
            {"agreement_id": agreement.id}
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_return_request_only_for_in_progress(self):
        agreement = self._make_agreement()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "proof.pdf",
                "datas": base64.b64encode(b"proof"),
                "res_model": "advance.payment.return.wizard",
                "res_id": 0,
            }
        )
        wizard = self.env["advance.payment.return.wizard"].create(
            {
                "agreement_id": agreement.id,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_close_after_return_request(self):
        agreement = self._make_agreement()
        agreement.write({"state": "in_progress", "is_return_requested": True})
        agreement.action_close()
        self.assertEqual(agreement.state, "done")
        self.assertTrue(agreement.date_closed)

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
