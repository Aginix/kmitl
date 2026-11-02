{
    "name": "Purchase Request Budget Cross-charge",
    "summary": "ถัวจ่าย on a พ.1: Reserve opens the ใบจองงบประมาณ as a dialog",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "KMITL/Budgeting",
    "depends": ["purchase_request_budget", "budget_commitment_cross_charge"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_commitment_views.xml",
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "AGPL-3",
}
