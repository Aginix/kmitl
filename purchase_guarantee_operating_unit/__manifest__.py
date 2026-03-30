# -*- coding: utf-8 -*-
{
    "name": "Purchase Guarantee with Operating Units",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "operating_unit",
        "purchase_guarantee_account_payment",
        "purchase_operating_unit",
        "purchase_request_operating_unit",
    ],
    "data": [
        "security/purchase_guarantee_security.xml",
        "views/purchase_guarantee_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
