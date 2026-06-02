# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class ReceiptKmitlCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # --- Analytic plans / accounts (6D framework relies on existing plans) ---
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
        cls.fund_general = Analytic.create(
            {"name": "General Fund", "code": "0100", "plan_id": cls.fund_plan.id}
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
        cls.suspense_edu = Account.create(
            {
                "code": "213101",
                "name": "Suspense - Education",
                "account_type": "liability_current",
                "company_id": cls.company.id,
            }
        )
        cls.suspense_other = Account.create(
            {
                "code": "213199",
                "name": "Suspense - Other",
                "account_type": "liability_current",
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

        # --- Journals ---
        Journal = cls.env["account.journal"]
        cls.cash_journal = Journal.create(
            {
                "name": "KMITL Cash",
                "type": "cash",
                "code": "CSHK",
                "is_receipt_kmitl_journal": True,
                "default_account_id": cls.cash_account.id,
                "company_id": cls.company.id,
            }
        )
        cls.general_journal = Journal.search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)], limit=1
        )
        if not cls.general_journal:
            cls.general_journal = Journal.create(
                {
                    "name": "Miscellaneous",
                    "type": "general",
                    "code": "MISC",
                    "company_id": cls.company.id,
                }
            )

        # --- Receipt types ---
        Type = cls.env["receipt.kmitl.type"]
        cls.type_edu = Type.create(
            {
                "name": "Education",
                "code": "EDU_TEST",
                "suspense_account_id": cls.suspense_edu.id,
                "default_income_account_id": cls.income_tuition.id,
            }
        )
        cls.type_other = Type.create(
            {
                "name": "Other",
                "code": "OTHER_TEST",
                "suspense_account_id": cls.suspense_other.id,
            }
        )

        # --- Walk-in partner ---
        cls.walkin = cls.env.ref(
            "receipt_kmitl.partner_walkin", raise_if_not_found=False
        )
        if not cls.walkin:
            cls.walkin = cls.env["res.partner"].create({"name": "Walk-in (test)"})

        # --- User with both depts ---
        cls.env.user.write({"kmitl_department_ids": [(6, 0, [cls.dept_a.id, cls.dept_b.id])]})

    def _make_receipt(self, department=None, lines=None, payment_method="cash"):
        department = department or self.dept_a
        lines = lines or [(self.type_edu, "ค่าลงทะเบียน", 1, 5000.0)]
        return self.env["receipt.kmitl"].create(
            {
                "department_id": department.id,
                "journal_id": self.cash_journal.id,
                "payment_method": payment_method,
                "partner_id": self.walkin.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "receipt_type_id": rtype.id,
                            "name": name,
                            "suspense_account_id": rtype.suspense_account_id.id,
                            "quantity": qty,
                            "price_unit": price,
                        },
                    )
                    for (rtype, name, qty, price) in lines
                ],
            }
        )
