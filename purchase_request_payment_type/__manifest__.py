# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Payment Type",
    "version": "16.0.1.0.0",
    "category": "Purchase Management",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "l10n_th_gov_purchase_request",
        "purchase_order_payment_type",
        "purchase_order_link_purchase_request"
    ],
    "data": ["data/purchase_exception.xml", "views/purchase_request_views.xml"],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
