# -*- coding: utf-8 -*-
{
    "name": "KMITL Advance Payment — e-Saraban Approval",
    "summary": "Route an Advance Payment (สัญญายืมเงิน) approval through e-Saraban",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": [
        "advance_payment",
        "agx_sarabun",
    ],
    "data": [
        "security/security.xml",
        "data/sarabun_advance_payment_data.xml",
        "views/advance_payment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
