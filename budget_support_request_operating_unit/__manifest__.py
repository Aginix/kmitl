{
    "name": "KMITL Budget Support Request — Operating Unit",
    "version": "16.0.1.0.0",
    "summary": """ Scope budget support requests to Operating Units """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_support_request",
        "budget_operating_unit",
    ],
    "data": [
        "security/budget_security.xml",
        "views/budget_support_request_views.xml",
    ],
    # Wherever both budget_support_request and budget_operating_unit are
    # present, requests must always carry an Operating Unit for scoping —
    # mirrors budget_operating_unit's own auto-install-adjacent siblings
    # (budget_transfer_sarabun, ADR-0014).
    "auto_install": True,
    "application": False,
    "license": "LGPL-3",
}
