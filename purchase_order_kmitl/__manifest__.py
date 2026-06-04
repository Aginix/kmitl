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
        "purchase_invoice_plan",
        "account_fiscal_year",
        "account_analytic_plan_code",
        "purchase_operating_unit",
        "purchase_request_department",
        "purchase_order_link_purchase_request",
        "purchase_contract_kmitl",
        # payment type merged into this module
        "purchase_exception",
        "purchase_stock",
    ],
    "data": [
        "views/purchase_order_views.xml",
        "views/purchase_order_views_invisible.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
