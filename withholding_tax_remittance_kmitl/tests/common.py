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

    def _make_cert(
        self, income_tax_form="pnd53", wht_tax=None, amount=300.0, base=10000.0
    ):
        wht_tax = wht_tax or self.wht_tax_53
        cert = self.env["withholding.tax.cert"].create(
            {
                "partner_id": self.vendor.id,
                "income_tax_form": income_tax_form,
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
        )
        cert.action_done()
        return cert
