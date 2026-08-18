# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Disbursement",
    "summary": "Track actual disbursement per procurement-plan installment (งวด)",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["procurement_plan_budget", "disbursement", "budget_product"],
    "data": [
        "security/ir.model.access.csv",
        "views/procurement_plan_views.xml",
        "views/disbursement_request_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
