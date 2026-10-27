# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Stations",
    "summary": "Route the disbursement request through stations: who holds it, "
    "which acts they may do, and where it goes next",
    "version": "16.0.1.0.1",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement", "work_center"],
    "data": [
        "data/work_center_data.xml",
        "views/disbursement_request_views.xml",
        "views/work_center_menus.xml",
    ],
    "installable": True,
    "auto_install": False,
}
