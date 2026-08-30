# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Receipt KMITL Operating Unit",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "Operating Unit access control for KMITL receipts and remittances",
    "depends": [
        "receipt_kmitl",
        "operating_unit",
        "account_operating_unit",
    ],
    "data": [
        "security/security.xml",
        "views/receipt_kmitl_views.xml",
        "views/receipt_remittance_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
