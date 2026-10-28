# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Approver (Rector Delegate) Budget",
    "summary": "The Rector-delegated approval also consumes the budget of the disbursement request",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_approver_rector", "disbursement_budget"],
    "data": ["views/disbursement_request_views.xml"],
    "installable": True,
    "auto_install": True,
}
