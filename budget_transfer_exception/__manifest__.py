{
    "name": "KMITL Budget Transfer Exception",
    "version": "16.0.1.0.0",
    "summary": """ base.exception framework for reviewing budget transfers on confirm """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_transfer",
        "base_exception",
    ],
    "data": [
        "security/ir.model.access.csv",
        # The review popup raised on ยืนยัน (_get_popup_action refs
        # action_budget_transfer_exception_confirm from here).
        "wizard/budget_transfer_exception_confirm_view.xml",
    ],
    # Framework layer only — ships no exception.rule. The concrete checks live in
    # thin bridge modules (budget_transfer_exception_kmitl_project /
    # budget_transfer_exception_procurement_plan). Auto-install wherever the
    # transfer feature meets base_exception, so the bridges can cascade on top.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
