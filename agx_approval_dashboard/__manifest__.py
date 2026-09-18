{
    "name": "Approval Dashboard (Biz-Portal UI)",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "summary": "Sidebar + card-grid dashboard replacing the default Approval "
               "Category kanban, styled after the government Biz Portal.",
    "depends": [
        "agx_approval",
    ],
    "data": [
        "views/dashboard_action.xml",
        "views/menu_override.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_approval_dashboard/static/src/components/**/*",
        ],
    },
    "installable": True,
    "auto_install": False,
}
