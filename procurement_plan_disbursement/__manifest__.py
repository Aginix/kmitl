{
    "name": "Procurement Plan Disbursement",
    "summary": "Track actual disbursement per procurement-plan installment (งวด)",
    "version": "16.0.1.4.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "procurement_plan_budget",
        "disbursement_budget",
        "disbursement_pdf",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/exception_rule_data.xml",
        "views/procurement_plan_views.xml",
        "views/disbursement_request_views.xml",
        "report/report_disbursement_request.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
