{
    "name": "e-Sarabun Widget Ztree",
    "summary": "ztree picker for e-Sarabun departments and positions",
    "version": "16.0.1.0.0",
    "category": "KMITL/Correspondence",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_sarabun",
        "app_web_widget_ztree_group",
        "hr_department_code",  # `code` ordering of the department tree
    ],
    "data": ["views/sarabun_views.xml"],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
