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
        "l10n_th_gov_purchase_request",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/procurement_plan_views.xml",
        "views/procurement_plan_menus.xml",
        "views/res_config_settings_views.xml",
        "report/report_procurement_plan.xml",
    ],
    "assets": {
        "web.assets_backend": ["procurement_plan/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
