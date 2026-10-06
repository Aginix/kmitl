# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Work Station: Verification",
    "summary": "The verification station of the disbursement route",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_wst"],
    "data": [
        "data/disbursement_station.xml",
        "data/disbursement_route_line.xml",
        "views/disbursement_request_views.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
