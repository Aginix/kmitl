# -*- coding: utf-8 -*-
{
    "name": "Purchase Request Report KMITL",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_request_kmitl",
        "purchase_request_budget",
        "purchase_request_department",
        "purchase_request_attachment",
        "l10n_th_amount_to_text",
        "l10n_th_fonts",
        "thai_date_utils",
        "purchase_request_price_tax_included"
    ],
    "data": [
        "reports/report_purchase_request.xml",
        "reports/paperformat_purchase_request.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
