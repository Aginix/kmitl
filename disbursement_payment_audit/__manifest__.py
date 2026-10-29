# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Payment Audit",
    "summary": "The ตรวจจ่าย act: the payment auditor checks a billed request's "
    "payees before authorization",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_finance_kmitl"],
    "data": ["views/disbursement_request_views.xml"],
    "installable": True,
    "auto_install": False,
}
