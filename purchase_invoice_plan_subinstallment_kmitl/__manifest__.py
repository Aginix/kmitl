# -*- coding: utf-8 -*-
{
    "name": "Purchase Invoice Plan Sub-Installment KMITL",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Split a purchase order installment (งวด) into sub-installments (งวดย่อย)",
    "depends": [
        "purchase_invoice_plan_kmitl",
        "purchase_work_acceptance_invoice_plan",
        "purchase_work_acceptance_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/add_sub_installment_wizard_views.xml",
        "views/purchase_invoice_plan_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
