# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Work Station: Billing",
    "summary": "The billing (ตั้งหนี้) station of the disbursement route",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "disbursement_wst",
        "disbursement_accounting_kmitl",
    ],
    "data": [
        # The billing station is held by the accounting office, whose group
        # implies no disbursement group: without these the station's holder
        # cannot read the steps its own request form renders.
        "security/ir.model.access.csv",
        "data/disbursement_station.xml",
        "data/disbursement_route_line.xml",
        "views/disbursement_request_views.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
