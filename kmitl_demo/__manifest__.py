# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "KMITL Demo",
    "version": "16.0.0.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "base",
        "account_kmitl",
        "hr_department_code",
        "account_fiscal_year",
        "account_analytic_kmitl",
        "hr_department_short_name",
    ],
    "data": [
        "data/company.xml",
        "data/hr.department.csv",
        "data/res.partner.xml",
        "data/res.bank.xml",
        "data/res.partner.bank.xml",
        "data/account.fiscal.year.csv",
        "data/ir_config_parameter.xml",
    ],
    "post_init_hook": "post_init",
    "uninstall_hook": "uninstall_hook",
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
