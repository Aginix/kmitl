{
    "name": "KMITL Budget Plan UI",
    "version": "16.0.1.0.0",
    "summary": """ Budget_plan_ui Summary """,
    "author": "Aginix Technologies",
    "website": "https://github.com/madara1150/budget",
    "category": "KMITL/Budgeting",
    "depends": [
        "base",
        "web",
        "account_analytic_parent",
        "procurement_plan",
        "budget"
    ],
    "data": [
        "views/procurement_inherit_view.xml",
        "security/ir.model.access.csv",
        "views/budget_appropriation_view.xml",
    ],
    "assets": {
        "web.assets_backend": ["budget_plan_ui/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
