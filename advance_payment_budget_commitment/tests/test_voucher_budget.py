from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVoucherBudget(TransactionCase):
    """ยืนยันส่งธนาคาร needs a loan voucher's 4 core dimensions and its
    รหัสงบประมาณ."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        admin = env.ref("base.user_admin")
        officer = env["res.users"].create(
            {
                "name": "Loan Officer",
                "login": "officer_apbc",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            env.ref(
                                "advance_payment.group_advance_payment_loan_officer"
                            ).id
                        ],
                    )
                ],
            }
        )
        employee = env["hr.employee"].search([("user_id", "=", admin.id)], limit=1)
        loan = env["advance.payment"].create(
            {
                "employee_id": employee.id,
                "loan_amount": 1000,
                "loan_type_id": env["advance.payment.loan.type"]
                .create({"name": "Test Loan Type"})
                .id,
                "loan_reason": "Test reason",
                "bank_id": env["res.partner.bank"]
                .create({"acc_number": "x-apbc", "partner_id": admin.partner_id.id})
                .id,
                "loan_verifier_id": officer.id,
            }
        )
        loan.write({"state": "approved"})
        loan.with_user(officer).action_create_payment_voucher()
        cls.payment = loan.payment_ids

        Plan = env["account.analytic.plan"]
        cls.distribution = {}
        for code in ("departments", "sources", "funds", "activities"):
            plan = Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": code, "code": code}
            )
            account = env["account.analytic.account"].create(
                {"name": "APBC %s" % code, "plan_id": plan.id}
            )
            cls.distribution[str(account.id)] = 100
        cls.budget_account = env["budget.account"].create(
            {
                "code": "APBC001",
                "name": "Test Budget Code",
                "budget_type": "expense",
                "budgetable": True,
            }
        )

    def test_confirm_refuses_incomplete_voucher(self):
        self.payment.analytic_distribution = False
        self.payment.budget_account_id = self.budget_account
        with self.assertRaisesRegex(UserError, "ส่วนงาน"):
            self.payment.action_confirm_for_bank()

    def test_confirm_refuses_voucher_without_budget_code(self):
        self.payment.analytic_distribution = self.distribution
        self.payment.budget_account_id = False
        with self.assertRaisesRegex(UserError, "รหัสงบประมาณ"):
            self.payment.action_confirm_for_bank()

    def test_complete_voucher_passes(self):
        self.payment.analytic_distribution = self.distribution
        self.payment.budget_account_id = self.budget_account
        self.assertTrue(self.payment.is_budget_code_required)
        self.payment._check_voucher_budget_complete()
