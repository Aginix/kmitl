# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Sarabun Preview",
    "summary": "Preview the หนังสือ a disbursement request will send to e-Saraban",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "disbursement_sarabun",
    ],
    "data": [
        "views/disbursement_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "disbursement_sarabun_preview/static/src/js/draft_preview.esm.js",
        ],
    },
    "installable": True,
    "auto_install": True,
}
