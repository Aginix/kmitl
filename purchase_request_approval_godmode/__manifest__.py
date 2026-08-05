# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Approval God Mode",
    "version": "16.0.1.0.0",
    "summary": "Elevated post-approval edit of พจ.1 (PA) header + line qty/price, capped by budget commitment.",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_request_approval",
        "purchase_request_budget",
    ],
    "data": [
        "security/purchase_request_approval_godmode.xml",
        "views/purchase_request_approval_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
