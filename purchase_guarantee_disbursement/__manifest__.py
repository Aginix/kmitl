{
    "name": "Purchase Guarantee Disbursement",
    "version": "16.0.1.0.0",
    "summary": "Return a security deposit through a disbursement request",
    "category": "Accounting/Accounting",
    "author": "KMITL",
    "website": "https://www.kmitl.ac.th",
    "depends": [
        "purchase_guarantee_receipt_kmitl",
        # Not plain `disbursement`: "returned" means the money actually left,
        # which only the payment-execution phase knows.
        "disbursement_finance_kmitl",
        # is_non_budget lives here, not in core — disbursement knows nothing
        # about budget after its ADR-0003.
        "disbursement_budget",
    ],
    "data": [
        "views/disbursement_request_views.xml",
        "views/purchase_guarantee_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
