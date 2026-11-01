# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Widget Ztree",
    "summary": "Ztree picker for the account on disbursement request lines",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement", "account_account_parent_code", "app_web_widget_ztree"],
    "data": [
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
