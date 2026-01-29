# -*- coding: utf-8 -*-
{
    'name': 'Budget Appropriation Report',
    "version": "16.0.1.0.0",
    "summary": "Budget Appropriation Report",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget_appropriation", "web"],
    "data": [
        "data/budget_appropriation_report_action.xml",
        "data/paper_format.xml",
        "security/ir.model.access.csv",
        "report/report_common.xml",
        "report/report_f2_revenue.xml",
        "report/report_f4p_revenue.xml",
        "report/report_f3w_f6w_revenue.xml",
        "report/report_f4w_revenue.xml",
        "report/report_f7w_expense.xml",
        "report/report_f5p_expense.xml",
        "report/report_f5w_expense.xml",
        "report/report_f8w_expense.xml",
        "report/report_f9w_expense.xml",
        "report/report_budget_appropriation_report.xml",
        "views/budget_appropriation_report_views.xml",
        "views/menus.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "budget_appropriation_report/static/src/**/*",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
