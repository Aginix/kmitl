# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Payment Subject Rules",
    "summary": "Pick a disbursement request's payment subject (เรื่องที่จ่าย) "
    "automatically by rules",
    "version": "16.0.1.1.0",
    "category": "KMITL/Finance",
    "website": "https://www.kmitl.ac.th",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_finance_kmitl"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_subject_rule_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
