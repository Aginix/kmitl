# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Budget",
    "summary": "Consume the linked budget commitment on the disbursement request's final approval",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "disbursement",
        # A DR consumes without obligating first; the budget ledger liquidates
        # the reservation for it (budget ADR-0017).
        "budget",
    ],
    "data": [
        "security/security.xml",
        "views/disbursement_request_views.xml",
        "views/budget_commitment_views.xml",
        "report/report_disbursement_request.xml",
    ],
    "installable": True,
    "auto_install": True,
}
