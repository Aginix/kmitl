# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class ReceiptKmitlCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # --- Analytic plans / accounts (6D framework) ---
        AnalyticPlan = cls.env["account.analytic.plan"]
        cls.dept_plan = AnalyticPlan.search([("code", "=", "departments")], limit=1)
        if not cls.dept_plan:
            cls.dept_plan = AnalyticPlan.create(
                {"name": "Departments", "code": "departments"}
            )
        cls.fund_plan = AnalyticPlan.search([("code", "=", "funds")], limit=1)
        if not cls.fund_plan:
            cls.fund_plan = AnalyticPlan.create({"name": "Funds", "code": "funds"})

        Analytic = cls.env["account.analytic.account"]
        cls.dept_a = Analytic.create(
            {"name": "Department A", "code": "01", "plan_id": cls.dept_plan.id}
        )
        cls.dept_b = Analytic.create(
            {"name": "Department B", "code": "02", "plan_id": cls.dept_plan.id}
        )

        # --- Accounts ---
        Account = cls.env["account.account"]
        cls.cash_account = Account.create(
            {
                "code": "111001",
                "name": "Cash on Hand",
                "account_type": "asset_cash",
                "company_id": cls.company.id,
            }
        )
        cls.bank_account = Account.create(
            {
                "code": "112001",
                "name": "Bank Clearing",
                "account_type": "asset_cash",
                "company_id": cls.company.id,
            }
        )
        cls.income_tuition = Account.create(
            {
                "code": "410101",
                "name": "Tuition Income",
                "account_type": "income",
                "company_id": cls.company.id,
            }
        )
        cls.income_other = Account.create(
            {
                "code": "419901",
                "name": "Other Income",
                "account_type": "income",
                "company_id": cls.company.id,
            }
        )

        # --- Journals ---
        Journal = cls.env["account.journal"]
        cls.cash_journal = Journal.create(
            {
                "name": "KMITL Cash",
                "type": "cash",
                "code": "CSHK",
                "default_account_id": cls.cash_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.bank_journal = Journal.create(
            {
                "name": "KMITL Bank",
                "type": "bank",
                "code": "BNKK",
                "default_account_id": cls.bank_account.id,
                "company_id": cls.company.id,
            }
        )

        # --- Payment methods ---
        Method = cls.env["kmitl.payment.method"]
        cls.pm_cash = Method.create(
            {
                "name": "Cash",
                "journal_id": cls.cash_journal.id,
                "account_id": cls.cash_account.id,
            }
        )
        cls.pm_transfer = Method.create(
            {
                "name": "Transfer",
                "journal_id": cls.bank_journal.id,
                "account_id": cls.bank_account.id,
            }
        )

        # --- Products (each carries an income account) ---
        Product = cls.env["product.product"]
        cls.product_tuition = Product.create(
            {
                "name": "Tuition Fee",
                "type": "service",
                "property_account_income_id": cls.income_tuition.id,
                "lst_price": 5000.0,
            }
        )
        cls.product_card = Product.create(
            {
                "name": "Student Card Fee",
                "type": "service",
                "property_account_income_id": cls.income_other.id,
                "lst_price": 100.0,
            }
        )

        # --- Walk-in partner ---
        cls.walkin = cls.env.ref(
            "receipt_kmitl.partner_walkin", raise_if_not_found=False
        )
        if not cls.walkin:
            cls.walkin = cls.env["res.partner"].create({"name": "Walk-in (test)"})

    def _make_receipt(self, department=None, method=None, lines=None, extra_vals=None):
        department = department or self.dept_a
        method = method or self.pm_cash
        lines = lines or [(self.product_tuition, 1, 5000.0)]
        vals = {
            "department_analytic_id": department.id,
            "payment_method_id": method.id,
            "partner_id": self.walkin.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": product.name,
                        "account_id": product.property_account_income_id.id,
                        "quantity": qty,
                        "price_unit": price,
                    },
                )
                for (product, qty, price) in lines
            ],
        }
        if extra_vals:
            vals.update(extra_vals)
        return self.env["kmitl.receipt"].create(vals)
