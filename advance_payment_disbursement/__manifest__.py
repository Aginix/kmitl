{
    "name": "Advance Payment - Disbursement Bridge",
    "summary": "ใบเบิกชดใช้เงินยืม: an advance disbursement request clears its loan",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        # สถานะวันครบกำหนด shown on the request.
        "advance_payment_followup",
        "advance_payment_operating_unit",
        # The consume act (ตัดงบ) is what clears the loan.
        "disbursement_budget",
        "disbursement_operating_unit",
    ],
    "data": [
        "views/disbursement_request_views.xml",
        "views/advance_payment_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
