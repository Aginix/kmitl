# -*- coding: utf-8 -*-
{
    "name": "Purchase Request UX KMITL",
    "version": "16.0.1.0.0",
    "category": "Purchase Management",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["l10n_th_gov_purchase_request", "purchase_request_kmitl", 'purchase_request_responsible_user', 'purchase_request_department', 'purchase_request_account_fiscal_year', 'purchase_request_payment_type', 'purchase_request_egp', 'purchase_request_operating_unit' ,'web_m2x_options'],
    "data": [
        "views/purchase_order_line_views.xml",
        "views/purchase_request_views.xml"
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
