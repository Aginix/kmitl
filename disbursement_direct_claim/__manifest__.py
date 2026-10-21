# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Disbursement Direct Claim",
    "summary": "ตั้งเบิกตรง: raise a disbursement request on an external memo, "
    "skipping the head's e-Saraban signature",
    "version": "16.0.1.0.0",
    "category": "Disbursement",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": ["disbursement"],
    "data": [
        "views/disbursement_request_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
