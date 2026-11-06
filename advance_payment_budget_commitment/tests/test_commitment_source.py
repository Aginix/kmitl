from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCommitmentSource(TransactionCase):
    """A ใบจองงบประมาณ as the loan's source, and its borrowed amount
    (ADR-0033)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.admin = env.ref("base.user_admin")
        cls.officer = env["res.users"].create(
            {
                "name": "Loan Officer",
                "login": "officer_apbc",
                "groups_id": [
                    (
                        6,
                        0,
                        env.ref(
                            "advance_payment.group_advance_payment_loan_officer"
                        ).ids,
                    )
                ],
            }
        )
        cls.loan_type = env.ref(
            "advance_payment_budget_commitment.loan_type_budget_commitment"
        )
        budget_account = env["budget.account"].create(
            {
                "code": "APBC001",
                "name": "Test Budget Code",
                "budget_type": "expense",
                "budgetable": True,
            }
        )
        cls.commitment = env["budget.commitment"].create(
            {"title": "APBC", "amount": 10000, "account_id": budget_account.id}
        )
        cls.commitment.write({"name": "BC-APBC-1", "state": "reserved"})
        cls.bank = env["res.partner.bank"].create(
            {"acc_number": "x-apbc", "partner_id": cls.admin.partner_id.id}
        )
        cls.employee = env["hr.employee"].search(
            [("user_id", "=", cls.admin.id)], limit=1
        )

    def _make(self, amount):
        return self.env["advance.payment"].create(
            {
                "employee_id": self.employee.id,
                "loan_amount": amount,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "bank_id": self.bank.id,
                "loan_verifier_id": self.officer.id,
                "reference": "budget.commitment,%s" % self.commitment.id,
            }
        )

    def test_commitment_is_found_by_number(self):
        loan = self._make(1000)
        self.assertEqual(loan._find_reference_by_number("bc-apbc-1 "), self.commitment)

    def test_loan_stores_the_commitment(self):
        loan = self._make(1000)
        self.assertEqual(loan.budget_commitment_id, self.commitment)
        self.assertEqual(
            self.env["advance.payment"].search(
                [("budget_commitment_id", "=", self.commitment.id)]
            ),
            loan,
        )

    def test_borrowed_amount_skips_drafts(self):
        draft = self._make(1000)
        submitted = self._make(3000)
        submitted.write({"state": "to_verify"})
        self.commitment.invalidate_recordset()
        self.assertEqual(self.commitment.advance_payment_count, 2)
        self.assertEqual(self.commitment.advance_payment_borrowed_amount, 3000)
        self.assertEqual(self.commitment.advance_payment_headroom, 7000)
        self.assertEqual(draft.borrowing_headroom, 7000)
        self.assertFalse(draft.exceeds_borrowing_headroom)

    def test_commitment_frozen_after_submit(self):
        loan = self._make(1000)
        loan.write({"state": "to_verify"})
        other = self.commitment.copy({"title": "APBC 2"})
        loan.reference = "budget.commitment,%s" % other.id
        self.assertEqual(loan.budget_commitment_id, self.commitment)

    def test_commitment_not_held_without_source(self):
        loan = self._make(1000)
        self.assertFalse(loan.is_commitment_held_by_source)
