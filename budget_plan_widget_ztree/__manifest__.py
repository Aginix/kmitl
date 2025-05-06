{
    "name": "Budget Plan Widget ztree",
    "version": "16.0.1.0.0",
    "summary": """ KMITL Budget Plan Widget ztree Summary """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget_plan", "app_web_widget_ztree"],
    "data": ["views/budget_plan_views.xml"],
    "assets": {
        "web.assets_backend": ["budget_plan_widget_ztree/static/src/**/*"],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
