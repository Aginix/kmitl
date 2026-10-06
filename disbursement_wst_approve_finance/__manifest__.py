# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Work Station: Finance Director Approval",
    "summary": "The finance director approval station of the disbursement route",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_wst"],
    "data": [
        "security/security.xml",
        "data/mail_activity_type.xml",
        "data/disbursement_station.xml",
        "data/disbursement_route_line.xml",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
}
