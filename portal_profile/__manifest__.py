{
    "name": "Portal Profile",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "category": "Website",
    "summary": "Portal profile page for personal information management",
    "depends": ["portal", "base_location"],
    "data": [
        "security/ir.model.access.csv",
        "views/portal_profile_views.xml",
        "views/res_partner_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
