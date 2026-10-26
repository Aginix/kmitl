{
    "name": "Aginix Approval Designated Budget Confirmer Operating Unit",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "ผู้ยืนยันงบประมาณ เลือกได้เฉพาะผู้ใช้ในหน่วยปฏิบัติงาน (OU) ของคำขอ",
    "depends": [
        "agx_approval_budget_verifier",
        # its form view carries the ungated invisible operating_unit_id
        "agx_approval_verifier_operating_unit",
    ],
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
