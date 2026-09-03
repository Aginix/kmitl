# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class WithholdingTaxRemittanceCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        Account = cls.env["account.account"]
        cls.wht_account_53 = Account.create(
            {
                "code": "212099",
                "name": "ภาษีหัก ณ ที่จ่ายรอนำส่ง (PND53)",
                "account_type": "liability_current",
                "wht_account": True,
                "company_id": cls.company.id,
            }
        )
        cls.wht_account_1 = Account.create(
            {
                "code": "212001",
                "name": "ภาษีหัก ณ ที่จ่ายรอนำส่ง (PND1)",
                "account_type": "liability_current",
                "wht_account": True,
                "company_id": cls.company.id,
            }
        )
        cls.savings_account = Account.create(
            {
                "code": "111002",
                "name": "Savings account for remittance",
                "account_type": "asset_cash",
                "company_id": cls.company.id,
            }
        )
        cls.current_account = Account.create(
            {
                "code": "111003",
                "name": "Current account for remittance",
                "account_type": "asset_cash",
                "company_id": cls.company.id,
            }
        )
        cls.expense_account = Account.create(
            {
                "code": "520001",
                "name": "Expense for source entries",
                "account_type": "expense",
                "company_id": cls.company.id,
            }
        )

        cls.wht_tax_53 = cls.env["account.withholding.tax"].create(
            {
                "name": "WHT 3% (53)",
                "account_id": cls.wht_account_53.id,
                "amount": 3.0,
                "income_tax_form": "pnd53",
                "company_id": cls.company.id,
            }
        )
        cls.wht_tax_1 = cls.env["account.withholding.tax"].create(
            {
                "name": "WHT 5% (1)",
                "account_id": cls.wht_account_1.id,
                "amount": 5.0,
                "income_tax_form": "pnd1",
                "company_id": cls.company.id,
            }
        )

        cls.journal_general = cls.env["account.journal"].create(
            {
                "name": "WHT Remittance Test Journal",
                "type": "general",
                "code": "WHTRT",
                "company_id": cls.company.id,
            }
        )

        cls.vendor = cls.env["res.partner"].create({"name": "Test Vendor"})
        cls.rd_partner = cls.env["res.partner"].create({"name": "กรมสรรพากร"})

        Plan = cls.env["account.analytic.plan"]
        analytic_plan = Plan.create({"name": "WHT Remittance Test Plan"})
        # code เป็น unique ทั้งระบบ และ account_analytic_kmitl ส่ง plan "sources"
        # มาเป็น data อยู่แล้ว — ใช้ตัวที่มีถ้ามี
        cls.plan_sources = Plan.search([("code", "=", "sources")], limit=1) or Plan.create(
            {"name": "แหล่งเงิน (test)", "code": "sources"}
        )
        Analytic = cls.env["account.analytic.account"]
        cls.analytic_dept_a = Analytic.create(
            {"name": "Dept A", "plan_id": analytic_plan.id, "company_id": cls.company.id}
        )
        cls.analytic_dept_b = Analytic.create(
            {"name": "Dept B", "plan_id": analytic_plan.id, "company_id": cls.company.id}
        )
        cls.source_1 = Analytic.create(
            {
                "name": "งบประมาณแผ่นดิน (test)",
                "plan_id": cls.plan_sources.id,
                "company_id": cls.company.id,
            }
        )
        cls.source_2 = Analytic.create(
            {
                "name": "เงินรายได้ (test)",
                "plan_id": cls.plan_sources.id,
                "company_id": cls.company.id,
            }
        )
        # ทุก distribution ที่ใช้ในเทสต์ต้องมีมิติแหล่งเงิน ไม่งั้นนำส่งไม่ได้
        cls.distribution_a = {
            str(cls.analytic_dept_a.id): 100.0,
            str(cls.source_1.id): 100.0,
        }
        cls.distribution_b = {
            str(cls.analytic_dept_b.id): 100.0,
            str(cls.source_1.id): 100.0,
        }
        cls.distribution_source_2 = {
            str(cls.analytic_dept_a.id): 100.0,
            str(cls.source_2.id): 100.0,
        }
        cls.distribution_two_sources = {
            str(cls.source_1.id): 100.0,
            str(cls.source_2.id): 100.0,
        }

    def _make_source_move(self, wht_tax, amount, analytic_distribution, date):
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal_general.id,
                "date": date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Vendor bill",
                            "account_id": self.expense_account.id,
                            "debit": amount,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT",
                            "account_id": wht_tax.account_id.id,
                            "debit": 0.0,
                            "credit": amount,
                            "wht_tax_id": wht_tax.id,
                            "analytic_distribution": analytic_distribution,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _make_cert(
        self,
        income_tax_form="pnd53",
        wht_tax=None,
        amount=300.0,
        base=10000.0,
        date="2026-01-15",
        name=None,
        analytic_distribution=None,
        source_move=None,
    ):
        """``analytic_distribution=None`` = ใช้ ``distribution_a`` (มีแหล่งเงิน)

        ส่ง ``False`` เมื่อต้องการใบรับรองที่ไม่มีมิติเลย หรือส่ง ``source_move``
        เมื่อต้องคุมบรรทัด WHT ต้นทางเอง
        """
        wht_tax = wht_tax or self.wht_tax_53
        if analytic_distribution is None:
            analytic_distribution = self.distribution_a
        vals = {
            "partner_id": self.vendor.id,
            "income_tax_form": income_tax_form,
            "date": date,
            "wht_line": [
                (
                    0,
                    0,
                    {
                        "wht_cert_income_type": "5",
                        "wht_cert_income_desc": "ค่าจ้างทำของ",
                        "base": base,
                        "wht_tax_id": wht_tax.id,
                        "amount": amount,
                    },
                )
            ],
        }
        if name:
            vals["name"] = name
        if source_move:
            vals["move_id"] = source_move.id
        elif analytic_distribution:
            vals["move_id"] = self._make_source_move(
                wht_tax, amount, analytic_distribution, date
            ).id
        cert = self.env["withholding.tax.cert"].create(vals)
        cert.action_done()
        return cert

    def _make_remittance(self, certs, month="1", year="2569", source=None):
        return self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": certs[0].income_tax_form,
                "period_month": month,
                "period_year": year,
                "source_analytic_id": (source or self.source_1).id,
                "cert_ids": [(6, 0, certs.ids)],
            }
        )

    def _set_bank_accounts(self, remittance):
        remittance.write(
            {
                "savings_account_id": self.savings_account.id,
                "current_account_id": self.current_account.id,
                "journal_id": self.journal_general.id,
            }
        )
        return remittance
