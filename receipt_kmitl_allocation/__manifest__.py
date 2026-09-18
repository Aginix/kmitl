# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Receipt KMITL Allocation",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "Posting-time revenue allocation (การปันส่วนรายได้) for KMITL receipts",
    "depends": [
        "receipt_kmitl",
        "account_analytic_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
    ],
    "installable": True,
    "application": False,
}
