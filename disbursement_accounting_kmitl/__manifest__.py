# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement ↔ KMITL Accounting Bridge",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "summary": "DR ↔ Bill: enable vendor bill creation from disbursement "
    "requests and pipeline status sync",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "depends": [
        "disbursement",
        "accounting_kmitl",
        "accounting_kmitl_workflow",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/disbursement_request_views.xml",
        "views/account_move_line_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
