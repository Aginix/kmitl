# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Invoice KMITL Operating Unit",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "summary": "Operating Unit access control for KMITL invoices and submissions",
    "depends": [
        "invoice_kmitl",
        "receipt_kmitl_operating_unit",
        "operating_unit",
        "account_operating_unit",
    ],
    "data": [
        "security/security.xml",
        "views/invoice_kmitl_views.xml",
        "views/invoice_submission_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
