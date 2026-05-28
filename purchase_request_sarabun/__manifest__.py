# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Sarabun Integration",
    "summary": "Integrate Purchase Request with Sarabun document routing",
    "version": "16.0.1.0.0",
    "category": "Purchases",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "purchase_request_kmitl",
        "purchase_request_budget",
        "purchase_request_department",
        "l10n_th_amount_to_text",
        "l10n_th_fonts",
        "thai_date_utils",
        "purchase_request_price_tax_included",
        "agx_sarabun",
        "portal",
    ],
    "data": [
        "data/sarabun_route_template_data.xml",
        "views/portal_templates.xml",
        "views/purchase_request_views.xml",
        "reports/paperformat_purchase_request.xml",
        "reports/report_purchase_request.xml"
    ],
    "assets": {
        'web.assets_frontend': [
            'purchase_request_sarabun/static/src/js/purchase_request_sidebar.js',
        ],
    },
    "installable": True,
    "auto_install": False,
}
