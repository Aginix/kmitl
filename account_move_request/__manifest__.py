# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Account Move Request",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/account_move_request_views.xml",
        "report/paperformat.xml",
        "report/report_account_move_request_action.xml",
        "report/report_account_move_request.xml",
        "views/portal_templates.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "account_move_request/static/src/js/account_move_request_sidebar.js",
        ],
    },
    "installable": True,
    "application": False,
}
