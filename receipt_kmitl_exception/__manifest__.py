# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Receipt KMITL Exception",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "Blocking/warning exception rules on KMITL receipt confirmation",
    "depends": [
        "receipt_kmitl",
        "base_exception",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/receipt_kmitl_exception_confirm_view.xml",
        "data/exception_data.xml",
    ],
    "installable": True,
    "auto_install": False,
}
