# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Partner Smart Buttons (KMITL)",
    "version": "16.0.1.0.0",
    "summary": "Smart buttons on the contact form linking to related KMITL documents",
    "category": "KMITL",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "disbursement",
        "advance_payment",
        "l10n_th_account_tax",
        "purchase_work_acceptance",
        "l10n_th_gov_purchase_guarantee",
        "purchase_request_approval",
    ],
    "data": ["views/res_partner_views.xml"],
    "installable": True,
}
