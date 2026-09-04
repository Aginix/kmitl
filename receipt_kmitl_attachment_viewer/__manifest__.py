# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Receipt KMITL - Attachment Viewer",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "Merged view-all-attachments PDF for receipt remittances",
    "depends": [
        "receipt_kmitl",
    ],
    "data": [
        "report/receipt_kmitl_attachments_separator.xml",
        "views/receipt_remittance_views.xml",
    ],
    "installable": True,
}
