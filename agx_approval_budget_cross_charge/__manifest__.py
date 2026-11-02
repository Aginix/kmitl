{
    "name": "Approval Request Budget Cross-charge",
    "summary": "ถัวจ่าย on a คำขออนุมัติ: ยืนยันงบประมาณ opens the ใบจองงบประมาณ as a dialog",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "development_status": "Beta",
    "category": "KMITL/Budgeting",
    "depends": ["agx_approval", "budget_commitment_cross_charge"],
    "data": [
        "security/ir.model.access.csv",
        "views/budget_commitment_views.xml",
        "views/approval_request_views.xml",
        "reports/report_approval_request.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "AGPL-3",
}
