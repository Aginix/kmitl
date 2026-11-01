{
    "name": "Advance Payment - Disbursement Bridge",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    # Only the ใบเบิก ↔ loan link. Nothing on a purchase request waits on or
    # copies a loan any more (advance_payment ADR-0029).
    "depends": [
        "advance_payment",
        "disbursement",
    ],
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
