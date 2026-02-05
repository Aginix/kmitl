# -*- coding: utf-8 -*-
{
    "name": "Purchase Request KMITL",
    "version": "16.0.1.0.0",
    "summary": """ Purchase Request KMITL""",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "l10n_th_gov_purchase_request",
        "purchase_request_operating_unit",
        "purchase_request_exception",
        "account_fiscal_year",
        "purchase_order_kmitl",
        "purchase_operating_unit",
        "purchase_contract_kmitl",
        "purchase_request_payment_type",
    ],
    "data": [
        "data/purchase_exception.xml",
        "data/purchase_request_exception.xml",
        "data/purchase_request_rules.xml",
        "data/procurement_type.xml",
        "views/procurement_committee_views.xml",
        "views/purchase_request_views.xml",
        "wizards/purchase_request_line_make_purchase_order_views.xml",
    ],
    'assets': {
              'web.assets_backend': [
                  'purchase_request_kmitl/static/src/**/*'
              ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
