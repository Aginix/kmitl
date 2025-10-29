# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Budget",
    "version": "16.0.1.0.0",
    "summary": """ Purchase Request Budget Summary """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "l10n_th_gov_purchase_request",
        "budget",
        "product_budget",
        "purchase_request_account_fiscal_year",
    ],
    "data": [
        "data/purchase_request_exception.xml",
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
