# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Work Stations",
    "summary": "Route a signed disbursement request through central work stations",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "disbursement",
        "base_state_leadtime",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/disbursement_route.xml",
        "views/disbursement_route_views.xml",
        "views/disbursement_request_views.xml",
        "views/disbursement_divert_wizard_views.xml",
    ],
    "installable": True,
}
