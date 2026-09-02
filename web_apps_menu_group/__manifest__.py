{
    "name": "Web Apps Menu Group",
    "summary": "Group the backend Apps grid menu into admin-defined categories",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "Hidden",
    "depends": ["web", "web_responsive"],
    "data": [
        "security/ir.model.access.csv",
        "views/apps_menu_group_views.xml",
        "views/ir_ui_menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_apps_menu_group/static/src/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "AGPL-3",
}
