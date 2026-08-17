{
    "name": "Procurement Plan",
    "version": "16.0.1.2.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["web", "account_analytic_kmitl", "account_fiscal_year", "l10n_th_base_sequence"],
    "data": [
        "data/account.analytic.plan.csv",
        "data/sequence.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/analytic_views.xml",
        "views/procurement_plan_views.xml",
        "views/procurement_plan_menus.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "procurement_plan/static/src/components/**/*",
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
