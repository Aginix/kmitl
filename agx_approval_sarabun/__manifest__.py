# -*- coding: utf-8 -*-
{
    "name": "Aginix Approval Sarabun Integration",
    "summary": "Integrate Approval Request with Sarabun document routing",
    "version": "16.0.1.0.1",
    "category": "Accounting",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "agx_approval",
        "l10n_th_amount_to_text",
        "l10n_th_fonts",
        "thai_date_utils",
        "agx_sarabun",
        "portal",
    ],
    "data": [
        "data/sarabun_route_template_data.xml",
        "views/approval_request_views.xml",
        "views/portal_templates.xml",
        "reports/report_approval_endorsement.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "agx_approval_sarabun/static/src/js/approval_request_sidebar.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
