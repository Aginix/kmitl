# -*- coding: utf-8 -*-
{
    "name": "Purchase Request e-GP",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["l10n_th_gov_purchase_request", "iframe_viewer_widget", 'purchase_request_kmitl', 'purchase_request_tier_validation'],
    "data": [
        "data/tier_validation_exception.xml",
        "views/purchase_request_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
