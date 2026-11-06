{
    "name": "Purchase Request: Current Fiscal Year Exception",
    "version": "16.0.1.0.0",
    "summary": """ Block submitting a purchase request unless its ปีงบประมาณ is the current one """,
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_request_kmitl",
    ],
    "data": [
        "data/exception_rule_data.xml",
    ],
    "auto_install": False,
    "application": False,
    "license": "AGPL-3",
}
