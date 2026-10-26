{
    "name": "Advance Payment - Exception Rules",
    "summary": "Blocking/warning exception rules on สัญญายืมเงิน submission",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "advance_payment",
        "base_exception",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/advance_payment_exception_data.xml",
        "wizards/advance_payment_exception_confirm.xml",
        "views/advance_payment_views.xml",
        "views/exception_rule_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    # The mandatory rules (missing bank account, reference, manager, amount
    # limits) live here, so every database with advance_payment gets them
    # (advance_payment ADR-0024).
    "auto_install": True,
    "license": "LGPL-3",
}
