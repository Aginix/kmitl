# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement — Change Requests",
    "summary": "The officer details what to fix on a disbursement request as "
    "change requests",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "disbursement_validation",
        "agx_change_request",
    ],
    "data": [
        "data/exception_rule_data.xml",
        "wizards/return_request_wizard_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
