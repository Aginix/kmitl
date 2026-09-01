# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "KMITL - Accounting",
    "version": "16.0.1.0.12",
    "category": "Accounting/Localizations/Account Charts",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    # partner_bank_code: res_bank.xml seeds ``bank_code``, which the
    # e-payment layouts write into the file as the receiving bank.
    "depends": ["account", "l10n_th", "l10n_th_account_tax", "partner_bank_code"],
    "data": [
        "data/res_bank.xml",
        "data/account_chart.xml",
        "data/account.account.template.csv",
        "data/account_chart_post.xml",
        "data/account_tax_group.xml",
        "data/account_tax_template.xml",
        "data/account_payment_method.xml",
    ],
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
}
