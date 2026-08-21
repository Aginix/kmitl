{
    "name": "Aginix Approval - Own Requests Security",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "summary": "Self-service role that only sees and files its own approval requests",
    "depends": [
        "agx_approval",
        "agx_approval_disbursement",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/approval_request_views.xml",
        "views/approval_menus.xml",
    ],
}
