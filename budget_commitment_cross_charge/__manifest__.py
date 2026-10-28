{
    "name": "Budget Commitment Cross-charge",
    "summary": "ถัวจ่าย: reserve one ใบจองงบประมาณ across several budget codes",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "KMITL/Budgeting",
    "depends": ["budget"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_account_views.xml",
        "views/budget_commitment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
