# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Sarabun Integration",
    "summary": "Route disbursement requests through Sarabun for head approval",
    "version": "16.0.1.1.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "disbursement",
        "agx_sarabun",
    ],
    "data": [
        "data/sarabun_route_template_data.xml",
        "views/disbursement_request_views.xml",
        "reports/report_disbursement_request.xml",
    ],
    "installable": True,
    "auto_install": False,
}
