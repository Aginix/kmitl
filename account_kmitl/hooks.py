from odoo import SUPERUSER_ID, api


def _create_journals(env, company):
    """Create KMITL journals after chart of accounts is loaded."""
    Account = env["account.account"]

    def get_account(code):
        return Account.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)

    journals_data = [
        {
            "name": "สมุดรายวันทั่วไป",
            "code": "JV",
            "type": "general",
            "company_id": company.id,
            "sequence": 10,
        },
        {
            "name": "สมุดรายวันจ่าย",
            "code": "PV",
            "type": "bank",
            "company_id": company.id,
            "default_account_id": get_account("1112210004").id or False,
            "sequence": 20,
        },
        {
            "name": "สมุดรายวันรับ",
            "code": "RV",
            "type": "bank",
            "company_id": company.id,
            "default_account_id": get_account("1112210004").id or False,
            "sequence": 30,
        },
        {
            "name": "สมุดรายวันขาย",
            "code": "SV",
            "type": "sale",
            "company_id": company.id,
            "default_account_id": get_account("4000000000").id or False,
            "sequence": 40,
        },
        {
            "name": "สมุดรายวันซื้อ",
            "code": "UV",
            "type": "purchase",
            "company_id": company.id,
            "default_account_id": get_account("5000000000").id or False,
            "sequence": 50,
        },
    ]

    Journal = env["account.journal"]
    for data in journals_data:
        existing = Journal.search(
            [("code", "=", data["code"]), ("company_id", "=", company.id)], limit=1
        )
        if not existing:
            Journal.create(data)


def _create_withholding_taxes(env, company):
    """Create KMITL withholding tax records after chart of accounts is loaded."""
    Account = env["account.account"]

    def get_account(code):
        return Account.search(
            [("code", "=", code), ("company_id", "=", company.id)], limit=1
        )

    # Mark WHT accounts
    for code in ("2120000010", "2120000099"):
        account = get_account(code)
        if account and not account.wht_account:
            account.wht_account = True

    wht_data = [
        {
            "name": "ภาษี หัก ณ ที่จ่ายบุคคลธรรมดา",
            "amount": 1.0,
            "account_id": get_account("2120000010").id,
            "income_tax_form": "pnd1",
            "wht_cert_income_type": "1",
        },
        {
            "name": "ภาษี หัก ณ ที่จ่ายนิติบุคคลจากหน่วยงานเอกชน",
            "amount": 1.0,
            "account_id": get_account("2120000099").id,
            "income_tax_form": "pnd53",
            "wht_cert_income_type": "5",
        },
    ]

    WHT = env["account.withholding.tax"]
    for data in wht_data:
        existing = WHT.search(
            [("name", "=", data["name"]), ("company_id", "=", company.id)], limit=1
        )
        if not existing:
            WHT.create({**data, "company_id": company.id})


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company")
    env.ref("account_kmitl.chart")._load(company)
    _create_journals(env, company)
    _create_withholding_taxes(env, company)
