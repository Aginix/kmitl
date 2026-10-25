import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerBankWizard(TransactionCase):
    """The loan officer materialises an unlisted bank account at verify
    (advance_payment ADR-0022)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Moving the loan into to_verify re-checks the blocking rules when
        # advance_payment_exception is installed; the dimension rule
        # (advance_payment_budget) needs master data these tests do not set up.
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].search(
                [
                    ("model", "=", "advance.payment"),
                    "|",
                    ("code", "ilike", "analytic_id"),
                    ("domain", "ilike", "department_id"),
                ]
            ).active = False
        cls.manager = cls.env.ref("base.user_admin")
        cls.officer = cls.env["res.users"].create(
            {
                "name": "Loan Officer",
                "login": "officer_ap_pb",
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
        cls.staff = cls.env["res.users"].create(
            {
                "name": "Staff",
                "login": "staff_ap_pb",
                "groups_id": [
                    (
                        6,
                        0,
                        cls.env.ref("advance_payment.group_advance_payment_user").ids,
                    )
                ],
            }
        )
        cls.emp = cls.env["hr.employee"].search(
            [("user_id", "=", cls.manager.id)], limit=1
        )
        cls.partner = cls.emp.work_contact_id
        cls.res_bank = cls.env["res.bank"].create({"name": "Test Bank"})
        cls.loan_type = cls.env["advance.payment.loan.type"].create(
            {"name": "Test Loan Type"}
        )

    def _loan(self, acc_number="123-4-56789-0"):
        loan = self.env["advance.payment"].create(
            {
                "employee_id": self.emp.id,
                "loan_amount": 1000,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "loan_verifier_id": self.officer.id,
                "use_unlisted_bank": True,
                "unlisted_bank_id": self.res_bank.id,
                "unlisted_acc_number": acc_number,
                "book_bank_file": base64.b64encode(b"book bank"),
            }
        )
        loan.write({"state": "to_verify", "bank_id": False})
        return loan

    def _wizard(self, loan, user=None, **vals):
        action = loan.action_open_partner_bank_wizard()
        return (
            self.env[action["res_model"]]
            .with_user(user or self.officer)
            .with_context(**action["context"])
            .create(vals)
        )

    def test_creates_account_and_unblocks_verify(self):
        loan = self._loan()
        wizard = self._wizard(loan)
        self.assertEqual(wizard.partner_id, self.partner)
        self.assertEqual(wizard.bank_id, self.res_bank)
        self.assertEqual(wizard.acc_number, "123-4-56789-0")
        wizard.action_apply()
        self.assertEqual(loan.bank_id.partner_id, self.partner)
        self.assertEqual(loan.bank_id.acc_number, "123-4-56789-0")
        self.assertFalse(loan.use_unlisted_bank)
        loan.with_user(self.officer).action_verify()
        self.assertEqual(loan.state, "to_approve")

    def test_officer_correction_is_used(self):
        loan = self._loan()
        self._wizard(loan, acc_number="999-9-99999-9").action_apply()
        self.assertEqual(loan.bank_id.acc_number, "999-9-99999-9")

    def test_reuses_existing_account_with_same_number(self):
        existing = self.env["res.partner.bank"].create(
            {"partner_id": self.partner.id, "acc_number": "1234567890"}
        )
        loan = self._loan(acc_number="123-4-56789-0")
        self._wizard(loan).action_apply()
        self.assertEqual(loan.bank_id, existing)

    def test_only_loan_officer_and_only_to_verify(self):
        loan = self._loan()
        with self.assertRaises(AccessError):
            self._wizard(loan).with_user(self.staff).action_apply()
        loan.write({"state": "draft"})
        with self.assertRaises(UserError):
            loan.action_open_partner_bank_wizard()
