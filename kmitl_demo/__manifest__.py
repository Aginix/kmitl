# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "KMITL Demo",
    "version": "16.0.0.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["base", "account", "account_kmitl", "hr"],
    "data": ["data/company.xml", "data/hr.department.csv"],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
