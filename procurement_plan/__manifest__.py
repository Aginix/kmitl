{
    "name": "Procurement Plan",
    "version": "16.0.1.0.3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "base",
        "web",
        "account_analytic_kmitl",
        "account_fiscal_year",
        "l10n_th_kmitl_procurement",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/procurement_plan_views.xml",
        "views/procurement_plan_menus.xml",
        "report/report_procurement_plan.xml",
        "report/report.xml"

    ],
    "assets": {
        "web.assets_backend": ["procurement_plan/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
