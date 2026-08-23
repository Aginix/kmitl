{
    "name": "Aginix Approval Disbursement",
    "version": "16.0.1.3.1",
    "category": "Accounting",
    "author": "KMITL",
    "depends": ["agx_approval", "disbursement"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_activity_type_data.xml",
        "data/approval_request_exception_data.xml",
        "views/approval_request_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
