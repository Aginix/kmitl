{
    "name": "Aginix Approval Disbursement",
    "version": "16.0.1.4.0",
    "category": "Accounting",
    "author": "KMITL",
    "depends": ["agx_approval", "disbursement_budget"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_activity_type_data.xml",
        "data/approval_request_exception_data.xml",
        "views/approval_request_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_approval_disbursement/static/src/js/many2many_binary_disbursement.js",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
