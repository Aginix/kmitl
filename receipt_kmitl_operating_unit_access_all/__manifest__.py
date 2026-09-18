# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Access all OUs' Receipt KMITL",
    "version": "16.0.1.0.0",
    "category": "KMITL/Accounting",
    "license": "AGPL-3",
    "author": "KMITL",
    "summary": "Bypass the KMITL receipt Operating Unit row-level rules",
    "depends": [
        "receipt_kmitl_operating_unit",
    ],
    "data": [
        "security/security.xml",
    ],
    "installable": True,
    "auto_install": False,
}
