# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement - Attachment Viewer",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "LGPL-3",
    "author": "KMITL",
    "summary": "Merged view-all-attachments PDF for disbursement requests",
    "depends": [
        "disbursement",
    ],
    "data": [
        "report/disbursement_attachments_separator.xml",
        "views/disbursement_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "disbursement_attachment_viewer/static/src/approval_queue/*.js",
            "disbursement_attachment_viewer/static/src/approval_queue/*.xml",
        ],
    },
    "installable": True,
}
