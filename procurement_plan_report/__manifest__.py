# -*- coding: utf-8 -*-
{
    "name": "Procurement Plan Report",
    "summary": "ส่งออกรายงานแผนจัดซื้อจัดจ้าง (procurement plan report export)",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    # Report needs the budget category (budget_account_id/is_asset) and the
    # พ.1 link + procurement method; report_xlsx drives the Excel export.
    # The disbursement layer (per-งวด actuals) is consumed optionally at runtime
    # — see docs/adr/0001 — so it is NOT a hard dependency.
    "depends": [
        "procurement_plan_budget",
        "purchase_request_procurement_plan",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/report_action_xlsx.xml",
        "views/procurement_plan_report_actions.xml",
        "views/procurement_plan_views.xml",
        "views/procurement_plan_report_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "procurement_plan_report/static/src/**/*",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
