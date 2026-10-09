# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Work Station: Payment Audit",
    "summary": "The payment audit (ตรวจสอบการเบิกจ่าย) station of the disbursement route",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_wst", "disbursement_finance_kmitl"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/mail_activity_type.xml",
        "data/disbursement_station.xml",
        "data/disbursement_route_line.xml",
        "views/disbursement_request_views.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
