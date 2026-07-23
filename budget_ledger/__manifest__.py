# -*- coding: utf-8 -*-
{
    "name": "Budget Ledger",
    "version": "16.0.1.0.0",
    "summary": "สมุดรายการเคลื่อนไหวงบประมาณ — timeline การจัดสรร/โอน/เบิกจ่าย",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": ["budget", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_ledger_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "budget_ledger/static/src/budget_ledger/budget_ledger.js",
            "budget_ledger/static/src/budget_ledger/budget_ledger.xml",
            "budget_ledger/static/src/budget_ledger/budget_ledger.scss",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
    "license": "AGPL-3",
}
