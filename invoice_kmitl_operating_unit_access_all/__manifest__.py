# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Access all OUs' Invoice KMITL",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "summary": "Bypass the KMITL invoice Operating Unit row-level rules",
    "depends": [
        "invoice_kmitl_operating_unit",
    ],
    "data": [
        "security/security.xml",
    ],
    "installable": True,
    "auto_install": False,
}
