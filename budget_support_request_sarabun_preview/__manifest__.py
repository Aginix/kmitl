# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "KMITL Budget Support Request — e-Saraban Preview",
    "summary": "Preview the หนังสือ a budget support request will send to e-Saraban",
    "version": "16.0.1.0.0",
    "category": "KMITL/Budgeting",
    "license": "LGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_support_request_sarabun",
    ],
    "data": [
        "views/budget_support_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_support_request_sarabun_preview/static/src/js/draft_preview.esm.js",
        ],
    },
    "installable": True,
    "auto_install": True,
}
