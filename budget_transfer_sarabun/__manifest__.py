{
    "name": "KMITL Budget Transfer — e-Saraban Approval",
    "summary": """ Route a Budget Transfer for approval (ขออนุมัติโอนงบประมาณ) """
    """ through e-Saraban """,
    "version": "16.0.1.0.0",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "AGPL-3",
    "depends": [
        "budget_transfer",
        "agx_sarabun",
        "budget_transfer_pdf",
    ],
    "data": [
        "data/sarabun_budget_transfer_data.xml",
        "views/budget_transfer_views.xml",
    ],
    # Wherever both budget_transfer and agx_sarabun are present the approval
    # route must never be silently absent (mirrors budget_transfer's own
    # auto-install philosophy, ADR-0014).
    "auto_install": True,
    "application": False,
}
