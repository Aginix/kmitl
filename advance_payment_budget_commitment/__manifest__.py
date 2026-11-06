{
    "name": "Advance Payment - Budget Commitment",
    "summary": "Borrow against a ใบจองงบประมาณ, cap borrowing at it and charge "
    "the disbursement voucher to its dimensions",
    "version": "16.0.1.2.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "advance_payment",
        "advance_payment_exception",
        "budget",
    ],
    "data": [
        "data/advance_payment_data.xml",
        "data/exception_rule_data.xml",
        "views/advance_payment_views.xml",
        "views/budget_commitment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
