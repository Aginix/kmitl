# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Sarabun Procurement Plan",
    "summary": "Print the แผนจัดซื้อจัดจ้าง row in the Sarabun disbursement body",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "disbursement_sarabun_budget",
        "procurement_plan_disbursement",
    ],
    "data": [
        "reports/report_disbursement_request.xml",
    ],
    "installable": True,
    "auto_install": True,
}
