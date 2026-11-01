{
    "name": "Aginix Approval Disbursement",
    "version": "16.0.2.0.0",
    "category": "Accounting",
    "author": "KMITL",
    "depends": ["agx_approval", "disbursement_budget"],
    "data": [
        "security/ir.model.access.csv",
        "views/approval_request_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "agx_approval_disbursement/static/src/disbursement_overview/*",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
