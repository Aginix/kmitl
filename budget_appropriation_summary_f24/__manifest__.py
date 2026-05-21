# -*- coding: utf-8 -*-
{
    "name": "Budget Appropriation Summary F24",
    "summary": "รายงาน F24",
    "author": "",
    "website": "",
    "category": "Accounting",
    "depends": [
        "budget_appropriation_summary",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/f24_config_data.xml",
        "report/report_compilation_f24.xml",
        "views/budget_appropriation_master_summary_views.xml",
        "views/budget_appropriation_summary_f24_config_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
