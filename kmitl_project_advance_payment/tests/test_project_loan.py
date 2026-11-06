from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectLoan(TransactionCase):
    """Borrowing against individual project expense items."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.admin = env.ref("base.user_admin")
        cls.officer = env["res.users"].create(
            {
                "name": "Loan Officer",
                "login": "officer_kpap",
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
        cls.loan_type = env.ref("kmitl_project_advance_payment.loan_type_kmitl_project")
        cls.bank = env["res.partner.bank"].create(
            {"acc_number": "x-kpap", "partner_id": cls.admin.partner_id.id}
        )
        cls.employee = env["hr.employee"].search(
            [("user_id", "=", cls.admin.id)], limit=1
        )
        fiscal_year = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-KPAP",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
            }
        )
        budget_account = env["budget.account"].create(
            {
                "code": "KPAP001",
                "name": "Test Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )
        cls.project = env["kmitl.project"].create(
            {
                "name": "Test Project",
                "project_type": "project",
                "account_fiscal_year_id": fiscal_year.id,
                "budget_account_id": budget_account.id,
                "budget_amount": 100000,
            }
        )
        cls.project.key = "PRJ-KPAP-1"
        commitment = env["budget.commitment"].create(
            {
                "title": "KPAP",
                "amount": 100000,
                "account_id": budget_account.id,
                "kmitl_project_id": cls.project.id,
                "account_fiscal_year_id": fiscal_year.id,
            }
        )
        commitment.write({"name": "BC-KPAP-1", "state": "reserved"})
        cls.project.write({"state": "in_progress"})
        Line = env["project.budget.line"]
        category = env.ref("kmitl_project.category_operating")
        cls.line = Line.create(
            {
                "project_id": cls.project.id,
                "budget_type": "expense",
                "name": "Honorarium",
                "category_id": category.id,
                "amount": 10000,
            }
        )
        cls.material = Line.create(
            {
                "project_id": cls.project.id,
                "budget_type": "expense",
                "name": "Supplies",
                "category_id": env.ref("kmitl_project.category_operating_materials").id,
                "amount": 5000,
            }
        )

    def _make(self, amount=1000):
        loan = self.env["advance.payment"].create(
            {
                "employee_id": self.employee.id,
                "loan_type_id": self.loan_type.id,
                "loan_reason": "Test reason",
                "bank_id": self.bank.id,
                "loan_verifier_id": self.officer.id,
                "reference": "kmitl.project,%s" % self.project.id,
            }
        )
        loan.action_load_project_lines()
        loan.project_line_ids.filtered(
            lambda line: line.project_line_id == self.line
        ).amount = amount
        return loan

    def test_found_by_project_number(self):
        loan = self._make()
        self.assertEqual(loan._find_reference_by_number(" prj-kpap-1"), self.project)

    def test_materials_not_loaded_nor_accepted(self):
        loan = self._make()
        self.assertEqual(loan.project_line_ids.project_line_id, self.line)
        with self.assertRaises(ValidationError):
            self.env["advance.payment.project.line"].create(
                {
                    "advance_payment_id": loan.id,
                    "project_line_id": self.material.id,
                    "amount": 100,
                }
            )

    def test_loan_amount_is_sum_of_items(self):
        loan = self._make(2500)
        self.assertEqual(loan.loan_amount, 2500)

    def test_remaining_counts_submitted_not_draft(self):
        draft = self._make(1000)
        submitted = self._make(3000)
        self.assertEqual(self.line.remaining_amount, 10000)
        submitted.write({"state": "to_verify"})
        self.assertEqual(self.line.remaining_amount, 7000)
        self.assertEqual(draft.project_line_ids.remaining_amount, 7000)
        submitted.write({"state": "cancel"})
        self.assertEqual(self.line.remaining_amount, 10000)

    def test_submit_blocked_over_remaining(self):
        self._make(8000).write({"state": "to_verify"})
        loan = self._make(3000)
        with self.assertRaises(ValidationError):
            loan.action_submit()
        self.assertEqual(loan.state, "draft")

    def test_item_amount_cannot_drop_below_borrowed(self):
        self._make(8000).write({"state": "to_verify"})
        with self.assertRaises(ValidationError):
            self.line.amount = 5000

    def test_lines_locked_after_submit(self):
        loan = self._make()
        loan.write({"state": "to_verify"})
        with self.assertRaises(ValidationError):
            loan.project_line_ids.amount = 1
