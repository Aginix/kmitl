import base64

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAdvancePaymentException(TransactionCase):
    """The submit-time rules moved out of advance_payment (ADR-0024)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The dimension rule (advance_payment_budget) needs master data these
        # tests do not set up — same lookup as advance_payment's own suite.
        cls.env["exception.rule"].search(
            [
                ("model", "=", "advance.payment"),
                "|",
                ("code", "ilike", "analytic_id"),
                ("domain", "ilike", "department_id"),
            ]
        ).active = False
        cls.manager = cls.env.ref("base.user_admin")
        Users = cls.env["res.users"]
        cls.officer = Users.create(
            {
                "name": "Loan Officer",
                "login": "officer_ap_exc",
                "groups_id": [
                    (
                        6,
                        0,
                        cls.env.ref(
                            "advance_payment.group_advance_payment_loan_officer"
                        ).ids,
                    )
                ],
            }
        )
        cls.supervisor = Users.create(
            {
                "name": "Supervisor",
                "login": "supervisor_ap_exc",
                "groups_id": [
                    (
                        6,
                        0,
                        cls.env.ref(
                            "advance_payment.group_advance_payment_own_only"
                        ).ids,
                    )
                ],
            }
        )
        Employee = cls.env["hr.employee"]
        cls.emp = Employee.search([("user_id", "=", cls.manager.id)], limit=1)
        cls.emp.parent_id = Employee.create(
            {"name": "Supervisor", "user_id": cls.supervisor.id}
        )
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )
        cls.bank = cls.env["res.partner.bank"].create(
            {"acc_number": "exc-1", "partner_id": cls.manager.partner_id.id}
        )
        cls.res_bank = cls.env["res.bank"].create({"name": "Test Bank"})

    def _make(self, employee=None, **vals):
        return self.env["advance.payment"].create(
            dict(
                {
                    "employee_id": (employee or self.emp).id,
                    "loan_amount": 1000,
                    "loan_type_id": self.loan_type.id,
                    "loan_reason": "Test reason",
                    "bank_id": self.bank.id,
                    "loan_verifier_id": self.officer.id,
                },
                **vals,
            )
        )

    def test_clean_request_submits(self):
        ap = self._make()
        ap.action_submit()
        self.assertEqual(ap.state, "to_endorse")

    def test_submit_blocked_by_zero_amount(self):
        ap = self._make(loan_amount=0)
        action = ap.action_submit()
        self.assertEqual(ap.state, "draft")
        self.assertEqual(action["res_model"], "advance.payment.exception.confirm")

    def test_submit_blocked_when_borrower_has_no_manager(self):
        """excep_missing_manager (ADR-0020)."""
        employee = self.env["hr.employee"].create({"name": "Manager-less Employee"})
        ap = self._make(employee=employee)
        ap.action_submit()
        self.assertEqual(ap.state, "draft")

    def test_submit_blocked_when_manager_has_no_user(self):
        userless_manager = self.env["hr.employee"].create({"name": "Userless Manager"})
        employee = self.env["hr.employee"].create(
            {"name": "Employee", "parent_id": userless_manager.id}
        )
        ap = self._make(employee=employee)
        ap.action_submit()
        self.assertEqual(ap.state, "draft")

    def test_officer_amount_edit_in_to_verify_is_checked(self):
        """The officer may correct loan_amount in to_verify (ADR-0005), so
        that edit faces the same blocking rules the borrower's submit did."""
        ap = self._make()
        ap.action_submit()
        ap.action_endorse()
        with self.assertRaises(ValidationError):
            ap.with_user(self.officer).write({"loan_amount": 60000})

    def test_missing_manager_does_not_block_officer_in_to_verify(self):
        """excep_missing_manager is scoped to draft/to_endorse."""
        ap = self._make()
        ap.action_submit()
        ap.action_endorse()
        self.emp.parent_id = False
        ap.with_user(self.officer).write({"loan_amount": 4200})
        self.assertEqual(ap.loan_amount, 4200)

    # ------------------------------------------------------------------ #
    # Missing bank account vs. unlisted bank account (ADR-0022)            #
    # ------------------------------------------------------------------ #

    def test_submit_blocked_without_bank(self):
        ap = self._make(bank_id=False)
        ap.action_submit()
        self.assertEqual(ap.state, "draft")

    def test_partial_unlisted_bank_still_blocks(self):
        ap = self._make(
            bank_id=False,
            use_unlisted_bank=True,
            unlisted_bank_id=self.res_bank.id,
            unlisted_acc_number="1234567890",
        )
        ap.action_submit()
        self.assertEqual(ap.state, "draft")

    def test_full_unlisted_bank_submits(self):
        ap = self._make(
            bank_id=False,
            use_unlisted_bank=True,
            unlisted_bank_id=self.res_bank.id,
            unlisted_acc_number="1234567890",
            book_bank_file=base64.b64encode(b"book bank"),
            book_bank_filename="bookbank.png",
        )
        ap.action_submit()
        self.assertEqual(ap.state, "to_endorse")
