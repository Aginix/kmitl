# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Purchase Request Sarabun Preview",
    "summary": "Preview the หนังสือ a purchase request will send to e-Saraban",
    "version": "16.0.1.0.0",
    "category": "Purchases",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "purchase_request_sarabun",
    ],
    "data": [
        "views/purchase_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_request_sarabun_preview/static/src/js/draft_preview.esm.js",
        ],
    },
    "installable": True,
    "auto_install": True,
}
