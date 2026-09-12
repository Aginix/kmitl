# -*- coding: utf-8 -*-
{
    "name": "Purchase Contract Revision KMITL",
    "version": "16.0.1.0.0",
    "summary": "Redesigned PO revision as first-class Contract records with attachment gate",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_contract_kmitl",
        "purchase_order_kmitl",
        "purchase_invoice_plan_kmitl",
        "purchase_work_acceptance_kmitl",
        "purchase_order_disbursement",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/purchase_contract_views.xml",
        "views/purchase_order_views.xml",
        "report/contract_amendment_report.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
