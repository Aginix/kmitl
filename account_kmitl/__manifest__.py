# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "KMITL - Accounting",
    "version": "16.0.1.0.1",
    "category": "Accounting/Localizations/Account Charts",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["account", "l10n_th"],
    "data": [
        "data/account_kmitl_chart_data.xml",
        "data/account.account.template.csv",
        "data/account_kmitl_chart_post_data.xml",
        "data/account_journal.xml",
        # "data/account_tax_template_data.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
}
