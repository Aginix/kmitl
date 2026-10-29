from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLoanTypeGroup(TransactionCase):
    """Restricted loan types limit who may start a loan (ADR-0031)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env["res.users"]
        cls.officer = Users.create(
            {
                "name": "Loan Officer",
                "login": "officer_ap_ltg",
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
        cls.borrower = Users.create(
            {
                "name": "Borrower",
                "login": "borrower_ap_ltg",
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
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Borrower", "user_id": cls.borrower.id}
        )
        cls.restricted = cls.env.ref("advance_payment.loan_type_other")
        cls.open_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Open Type"}
        )

    def _make(self, user, loan_type):
        return (
            self.env["advance.payment"]
            .with_user(user)
            .create(
                {
                    "employee_id": self.employee.id,
                    "loan_amount": 1000,
                    "loan_type_id": loan_type.id,
                    "loan_reason": "Test reason",
                    "loan_verifier_id": self.officer.id,
                }
            )
        )

    def test_no_source_type_restricted_to_officer_on_install(self):
        self.assertIn(
            self.env.ref("advance_payment.group_advance_payment_loan_officer"),
            self.restricted.group_ids,
        )

    def test_selectable_types_follow_groups(self):
        LoanType = self.env["advance.payment.loan.type"]
        offered = LoanType.with_user(self.borrower).search(
            [("is_selectable", "=", True)]
        )
        self.assertIn(self.open_type, offered)
        self.assertNotIn(self.restricted, offered)
        self.assertIn(
            self.restricted,
            LoanType.with_user(self.officer).search([("is_selectable", "=", True)]),
        )

    def test_borrower_cannot_start_restricted_type(self):
        with self.assertRaises(ValidationError):
            self._make(self.borrower, self.restricted)
        self.assertTrue(self._make(self.borrower, self.open_type))

    def test_borrower_may_edit_loan_drafted_by_officer(self):
        loan = self._make(self.officer, self.restricted)
        loan.with_user(self.borrower).write({"loan_amount": 2000})
        self.assertEqual(loan.loan_amount, 2000)
