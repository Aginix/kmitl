{
    "name": "KMITL Project Budget Transfer PDF",
    "version": "16.0.1.0.0",
    "summary": "เอกสารแนบท้าย งปม.303 แจกแจงโครงการ/กิจกรรมที่ปรากฏในใบโอนงบ",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "kmitl_project_budget_transfer",
        "budget_transfer_pdf",
    ],
    "data": [
        "report/report_budget_transfer.xml",
    ],
    # Auto-install wherever a project-tagged transfer can be printed as งปม.303.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
