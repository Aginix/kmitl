{
    "name": "Purchase Request Todos",
    "version": "16.0.2.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "summary": "Activity type definitions for the พ.1 / พจ.1 Todo lifecycle, "
    "and PA (พจ.1) workflow Todos (status FYI, manager consideration, "
    "record contract, PO creation)",
    "depends": [
        "base_automation",
        "mail_activity_todo_role_unit",
        "purchase_request_approval",
        # FIXME(rebase 2026-09): origin/16.0 dropped these five explicit deps
        # (2d0c762a2) after rewriting this module's Todo scheduling onto
        # base.automation + a new purchase_request_budget_todo module — this
        # branch still needs them because its own models/purchase_request.py
        # (Python-hook based) references purchase_request_kmitl's states,
        # purchase_request_sarabun/_egp's callbacks, and budget_role's xmlid
        # directly. Needs reconciling with the upstream rewrite before merge.
        "purchase_request_activity_kmitl",
        "purchase_request_kmitl",
        "purchase_request_sarabun",
        "purchase_request_egp",
        "budget_role",
        "purchase_user_role",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/base_automation.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
