{
    "name": "KMITL Project Disbursement",
    "version": "16.0.1.4.0",
    "category": "KMITL",
    "summary": "Link disbursement requests (ใบขอเบิก) raised under a KMITL project",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project",
        "disbursement_budget",
        "disbursement_pdf",
    ],
    "data": [
        "data/exception_rule_data.xml",
        "views/kmitl_project_views.xml",
        "views/disbursement_request_views.xml",
        "report/report_disbursement_request.xml",
    ],
    "application": False,
    "installable": True,
    # Glue module: surface the project's disbursements automatically whenever both
    # sides are present (disbursement_pdf is pulled in, not a trigger).
    "auto_install": ["kmitl_project", "disbursement_budget"],
    "license": "LGPL-3",
}
