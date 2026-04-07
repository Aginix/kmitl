# -*- coding: utf-8 -*-
{
    "name": "Budget Appropriation Summary F3P",
    "summary": "รายงาน F3-P สรุปประมาณการรายรับ-รายจ่าย ประจำหน่วยงาน",
    "author": "",
    "website": "",
    "category": "Accounting",
    "depends": [
        "budget_appropriation_summary",
        "account_analytic_kmitl",
    ],
    "data": [
        "report/report_compilation_f3.xml",
        "views/budget_appropriation_compilation_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
