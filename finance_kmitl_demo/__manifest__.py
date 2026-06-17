# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "KMITL Finance Demo",
    "version": "16.0.0.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "summary": "Demo data for the post-budget finance flow: disbursement "
    "requests, vendor bills, payments, bank payment export and fixed assets.",
    "depends": [
        "kmitl_demo",
        "disbursement",
        "purchase_request_approval_work_acceptance",
        "agx_approval_disbursement",
        "disbursement_accounting_kmitl",
        "disbursement_finance_kmitl",
        "finance_kmitl",
        "accounting_kmitl",
        "account_asset_kmitl",
        "account_asset_depreciation_board",
        "l10n_th_gov_gpsc",
        "l10n_th_bank_payment_export_ktb",
    ],
    "data": [],
    "post_init_hook": "post_init",
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
