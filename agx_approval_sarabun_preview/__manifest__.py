# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Aginix Approval — e-Saraban Preview",
    "summary": "Preview the หนังสือ an approval request will send to e-Saraban",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_approval_sarabun",
    ],
    "data": [
        "views/approval_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_approval_sarabun_preview/static/src/js/draft_preview.esm.js",
        ],
    },
    "installable": True,
    "auto_install": True,
}
