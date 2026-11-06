{
    "name": "KMITL Project - Advance Payment",
    "summary": "ยืมเงินโครงการ: borrow against individual project expense items",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "advance_payment",
        "advance_payment_exception",
        "advance_payment_budget_commitment",
        "kmitl_project",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/advance_payment_data.xml",
        "views/advance_payment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
