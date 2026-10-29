from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRelatedDocument(TransactionCase):
    """Who may change a loan's related documents, and until when (ADR-0029)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env["res.users"]

        def user(login, group):
            return Users.create(
                {
                    "name": login,
                    "login": login,
                    "groups_id": [(6, 0, cls.env.ref(group).ids)],
                }
            )

        cls.borrower = user(
            "borrower_ap_rd", "advance_payment.group_advance_payment_own_only"
        )
        cls.unit_finance = user(
            "unit_finance_ap_rd", "advance_payment.group_advance_payment_user"
        )
        cls.officer = user(
            "officer_ap_rd", "advance_payment.group_advance_payment_loan_officer"
        )
        employee = cls.env["hr.employee"].create(
            {"name": "Borrower", "user_id": cls.borrower.id}
        )
        cls.loan = (
            cls.env["advance.payment"]
            .with_user(cls.borrower)
            .create(
                {
                    "employee_id": employee.id,
                    "loan_amount": 1000,
                    "loan_type_id": cls.env["advance.payment.loan.type"]
                    .create({"name": "Test Type"})
                    .id,
                    "loan_reason": "Test reason",
                    "loan_verifier_id": cls.officer.id,
                }
            )
            .sudo()
        )

    def _add(self, user, **vals):
        return (
            self.env["advance.payment.related.document"]
            .with_user(user)
            .create(
                dict(
                    {
                        "advance_payment_id": self.loan.id,
                        "document_number": "อว 0001/1",
                        "name": "หนังสือขยายเวลา",
                    },
                    **vals,
                )
            )
        )

    def test_borrower_adds_after_submit_and_it_is_logged(self):
        self.loan.state = "in_progress"
        messages = len(self.loan.message_ids)
        row = self._add(self.borrower)
        self.assertEqual(row.added_by_id, self.borrower)
        self.assertGreater(len(self.loan.message_ids), messages)

    def test_borrower_removes_own_row_only_in_draft(self):
        row = self._add(self.borrower)
        row.with_user(self.borrower).unlink()
        self.assertFalse(row.exists())
        row = self._add(self.borrower)
        self.loan.state = "to_verify"
        with self.assertRaises(UserError):
            row.with_user(self.borrower).unlink()

    def test_borrower_cannot_remove_staff_row(self):
        row = self._add(self.unit_finance)
        with self.assertRaises(UserError):
            row.with_user(self.borrower).unlink()

    def test_staff_remove_any_row_until_closed(self):
        self.loan.state = "in_progress"
        self._add(self.borrower).with_user(self.unit_finance).unlink()
        row = self._add(self.borrower)
        row.with_user(self.officer).unlink()
        self.assertFalse(row.exists())

    def test_closed_loan_is_frozen(self):
        row = self._add(self.borrower)
        self.loan.state = "done"
        with self.assertRaises(UserError):
            self._add(self.officer)
        with self.assertRaises(UserError):
            row.with_user(self.officer).unlink()

    def test_row_needs_number_or_subject(self):
        with self.assertRaises(ValidationError):
            self._add(self.borrower, document_number=False, name=False)
