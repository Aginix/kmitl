# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Operating Unit",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "license": "LGPL-3",
    "depends": [
        "operating_unit",
        "disbursement",
    ],
    "data": [
        "security/security.xml",
        "views/disbursement_request_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
}
