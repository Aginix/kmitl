# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Apportionment",
    "summary": "ปันส่วน: apportion part of a request's income to internal units "
    "by a budget transfer posted with its consume-budget act",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_direct_claim_budget", "budget_transfer"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/exception_rule_data.xml",
        "views/disbursement_request_views.xml",
        "views/budget_transfer_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
