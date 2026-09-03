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
        cls.bank_account = Account.create(
            {
                "code": "111002",
                "name": "Bank for remittance",
                "account_type": "asset_cash",
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

        analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "WHT Remittance Test Plan"}
        )
        cls.analytic_dept_a = cls.env["account.analytic.account"].create(
            {"name": "Dept A", "plan_id": analytic_plan.id, "company_id": cls.company.id}
        )
        cls.analytic_dept_b = cls.env["account.analytic.account"].create(
            {"name": "Dept B", "plan_id": analytic_plan.id, "company_id": cls.company.id}
        )
        cls.distribution_a = {str(cls.analytic_dept_a.id): 100.0}
        cls.distribution_b = {str(cls.analytic_dept_b.id): 100.0}

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
                            "account_id": self.bank_account.id,
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
    ):
        wht_tax = wht_tax or self.wht_tax_53
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
        if analytic_distribution is not None:
            vals["move_id"] = self._make_source_move(
                wht_tax, amount, analytic_distribution, date
            ).id
        cert = self.env["withholding.tax.cert"].create(vals)
        cert.action_done()
        return cert

    def _make_remittance(self, certs, month="1", year="2569"):
        return self.env["withholding.tax.remittance"].create(
            {
                "income_tax_form": certs[0].income_tax_form,
                "period_month": month,
                "period_year": year,
                "cert_ids": [(6, 0, certs.ids)],
            }
        )
