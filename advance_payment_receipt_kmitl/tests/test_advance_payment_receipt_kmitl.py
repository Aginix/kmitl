from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAdvancePaymentReceiptKmitl(TransactionCase):
    """The return settlement issues a kmitl.receipt instead of an
    account.payment (receipt replaces payment)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # --- Analytic: a department dimension for the receipt ---
        AnalyticPlan = cls.env["account.analytic.plan"]
        cls.dept_plan = AnalyticPlan.search(
            [("code", "=", "departments")], limit=1
        ) or AnalyticPlan.create({"name": "Departments", "code": "departments"})
        cls.dept = cls.env["account.analytic.account"].create(
            {"name": "Dept A", "code": "01", "plan_id": cls.dept_plan.id}
        )

        # --- Accounts / journal / payment method / product ---
        Account = cls.env["account.account"]
        cls.cash_account = Account.create(
            {
                "code": "111500",
                "name": "Cash on Hand (test)",
                "account_type": "asset_cash",
                "company_id": cls.company.id,
            }
        )
        cls.income_account = Account.create(
            {
                "code": "419500",
                "name": "Advance Return (test)",
                "account_type": "income",
                "company_id": cls.company.id,
            }
        )
        cls.cash_journal = cls.env["account.journal"].create(
            {
                "name": "Cash (test)",
                "type": "cash",
                "code": "CSHR",
                "default_account_id": cls.cash_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.method = cls.env["kmitl.payment.method"].create(
            {
                "name": "Cash return",
                "payment_type": "cash",
                "journal_id": cls.cash_journal.id,
                "account_id": cls.cash_account.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "รับคืนเงินยืม (test)",
                "detailed_type": "service",
                "property_account_income_id": cls.income_account.id,
            }
        )

        # --- Config params consumed by the bridge ---
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param(
            "advance_payment_receipt_kmitl.return_product_id", cls.product.id
        )
        ICP.set_param(
            "advance_payment_receipt_kmitl.return_payment_method_id",
            cls.method.id,
        )

        # --- Loan officer (approves returns) ---
        cls.officer = cls.env["res.users"].create(
            {
                "name": "Loan Officer",
                "login": "officer_ap_receipt",
                "email": "officer@test.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref(
                                "advance_payment."
                                "group_advance_payment_loan_officer"
                            ).id
                        ],
                    )
                ],
            }
        )

        # --- Borrower + employee so agreement.partner_id resolves ---
        cls.borrower = cls.env["res.users"].create(
            {
                "name": "Borrower",
                "login": "borrower_ap_receipt",
                "email": "borrower@test.local",
                "groups_id": [
                    (6, 0, [cls.env.ref("base.group_user").id])
                ],
            }
        )
        Employee = cls.env["hr.employee"]
        cls.employee = Employee.search(
            [("user_id", "=", cls.borrower.id)], limit=1
        ) or Employee.create({"name": "Borrower", "user_id": cls.borrower.id})
        cls.bank = cls.env["res.partner.bank"].create(
            {"acc_number": "ap-r-1", "partner_id": cls.borrower.partner_id.id}
        )

    def _make_reconcilable(self, loan=1000, expense=600):
        """An agreement already sitting in to_reconcile with return_amount>0."""
        agreement = self.env["advance.payment"].create(
            {
                "employee_id": self.employee.id,
                "loan_amount": loan,
                "loan_type_id": self.env["advance.payment.loan.type"]
                .create({"name": "T"})
                .id,
                "loan_reason": "test",
                "bank_id": self.bank.id,
                "loan_verifier_id": self.officer.id,
                "analytic_distribution": {str(self.dept.id): 100},
            }
        )
        agreement.write(
            {"state": "to_reconcile", "actual_expense_amount": expense}
        )
        return agreement

    def _return_line(self, agreement, amount):
        line = self.env["advance.payment.return.line"].create(
            {"agreement_id": agreement.id, "amount": amount}
        )
        line.action_confirm()
        return line

    def test_approve_issues_receipt_not_payment(self):
        agreement = self._make_reconcilable()
        line = self._return_line(agreement, 400)
        line.with_user(self.officer).action_approve()

        self.assertEqual(line.state, "done")
        self.assertFalse(line.payment_id, "no account.payment must be created")
        self.assertTrue(line.receipt_id, "a receipt must be issued")
        receipt = line.receipt_id
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.partner_id, agreement.partner_id)
        self.assertFalse(receipt.is_walkin)
        self.assertEqual(receipt.amount_total, 400)
        self.assertEqual(receipt.payment_method_id, self.method)
        self.assertEqual(receipt.department_analytic_id, self.dept)
        # fully returned -> agreement auto-closes (ADR-0003)
        self.assertEqual(agreement.state, "done")
        self.assertEqual(agreement.receipt_count, 1)

    def test_missing_config_raises(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "advance_payment_receipt_kmitl.return_product_id", ""
        )
        agreement = self._make_reconcilable()
        line = self._return_line(agreement, 400)
        with self.assertRaises(UserError):
            line.with_user(self.officer).action_approve()

    def test_admin_reset_cancels_draft_receipt(self):
        agreement = self._make_reconcilable()
        line = self._return_line(agreement, 400)
        line.with_user(self.officer).action_approve()
        receipt = line.receipt_id

        line.action_admin_reset()
        self.assertEqual(line.state, "draft")
        self.assertFalse(line.receipt_id)
        self.assertEqual(receipt.state, "cancelled")

    def test_admin_reset_blocked_when_receipt_left_draft_state(self):
        agreement = self._make_reconcilable()
        line = self._return_line(agreement, 400)
        line.with_user(self.officer).action_approve()
        # Simulate the receipt having advanced into the remittance workflow.
        line.receipt_id.state = "submitted"
        with self.assertRaises(UserError):
            line.action_admin_reset()
