# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Account Move Request - Withholding Tax",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "KMITL",
    "summary": "Add WHT support to Account Move Request",
    "depends": [
        "account_move_request",
        "l10n_th_account_tax",
    ],
    "data": [
        "views/account_move_request_views.xml",
    ],
    "installable": True,
    "application": False,
}
