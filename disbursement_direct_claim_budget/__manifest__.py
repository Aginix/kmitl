# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Direct Claim Budget",
    "summary": "ตั้งเบิกตรง without a reservation: consume the pool directly "
    "when its consume-budget act runs",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement_direct_claim", "disbursement_budget"],
    "data": [
        "data/exception_rule_data.xml",
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
