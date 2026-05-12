# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "KMITL Accounting Reports",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "summary": "รายงานบัญชี KMITL: งบกำไรขาดทุน, งบแสดงฐานะการเงิน, งบกระแสเงินสด",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "accounting_kmitl",
        # OCA building blocks (clone from OCA/account-financial-reporting 16.0)
        "mis_template_financial_report",
        "mis_builder_cash_flow",
        "account_financial_report",
    ],
    "data": [
        "data/mis_report_style_kmitl.xml",
        "data/mis_report_pl_kmitl.xml",
        "data/mis_report_bs_kmitl.xml",
        "data/mis_report_cf_kmitl.xml",
        "data/mis_report_instance_kmitl.xml",
        "views/menuitem.xml",
    ],
    "installable": True,
    "auto_install": False,
}
