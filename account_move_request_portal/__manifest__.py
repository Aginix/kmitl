# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Account Move Request Portal",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "LGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "account_move_request",
        "portal",
    ],
    "data": [
        "views/portal_templates.xml",
        "views/account_move_request_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "account_move_request_portal/static/src/js/account_move_request_portal_sidebar.js",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
}
