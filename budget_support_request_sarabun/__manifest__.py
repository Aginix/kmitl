{
    "name": "KMITL Budget Support Request — e-Saraban Approval",
    "summary": """ Route a Budget Support Request for approval """
    """ (ขออนุมัติสนับสนุนงบประมาณ) through e-Saraban """,
    "version": "16.0.1.0.0",
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "AGPL-3",
    "depends": [
        "budget_support_request",
        "agx_sarabun",
    ],
    "data": [
        "data/sarabun_budget_support_data.xml",
        "views/budget_support_request_views.xml",
    ],
    # Wherever both budget_support_request and agx_sarabun are present the
    # approval route must never be silently absent (mirrors
    # budget_transfer_sarabun's own auto-install philosophy, ADR-0014).
    "auto_install": True,
    "application": False,
}
