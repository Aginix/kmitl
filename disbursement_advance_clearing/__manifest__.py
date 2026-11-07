# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement - Advance Clearing",
    "summary": "ล้างลูกหนี้เงินยืม: a request that pays no money out is booked "
    "by a clearing entry (Dr expense / Cr advance receivable), not a bill",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "license": "LGPL-3",
    "depends": [
        "account_kmitl",
        "disbursement_bill_posted_confirm",
        "disbursement_finance_kmitl",
        "disbursement_payment_audit",
        "disbursement_payment_paid_confirm",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": True,
}
