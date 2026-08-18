# -*- coding: utf-8 -*-
{
    "name": "KMITL Project Disbursement",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "summary": "Link disbursement requests (ใบขอเบิก) raised under a KMITL project",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["kmitl_project", "disbursement", "budget_product"],
    "data": [
        "data/exception_rule_data.xml",
        "views/kmitl_project_views.xml",
        "views/disbursement_request_views.xml",
        "report/report_disbursement_request.xml",
    ],
    "application": False,
    "installable": True,
    # Glue module: surface the project's disbursements automatically whenever both
    # sides are present.
    "auto_install": True,
    "license": "LGPL-3",
}
