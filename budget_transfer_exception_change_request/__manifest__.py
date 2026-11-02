{
    "name": "KMITL Budget Transfer Exception: Change Requests",
    "version": "16.0.1.0.0",
    "summary": """ ยืนยันตรวจสอบ waits until no change request is outstanding """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_transfer_exception",
        "budget_transfer_change_request",
    ],
    "data": [
        "data/exception_rule_data.xml",
    ],
    # Auto-install wherever the transfer-exception framework meets change requests.
    "auto_install": True,
    "application": False,
    "license": "AGPL-3",
}
