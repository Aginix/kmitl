{
    "name": "Advance Payment - Borrower Bank Account",
    "summary": "Loan officer turns a borrower's unlisted bank account into a "
    "real one at verification",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": ["advance_payment"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/advance_payment_partner_bank_wizard_views.xml",
        "views/advance_payment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
