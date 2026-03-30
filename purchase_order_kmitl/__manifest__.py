# -*- coding: utf-8 -*-
{
    "name": "Purchase Order KMITL",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_requisition",
        "purchase_no_rfq",
        "purchase_invoice_plan_kmitl",
        "account_fiscal_year",
        "hr",
        "purchase_operating_unit",
        "purchase_request_department",
        "purchase_order_link_purchase_request",
    ],
    "data": ["views/purchase_order_views.xml"],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
