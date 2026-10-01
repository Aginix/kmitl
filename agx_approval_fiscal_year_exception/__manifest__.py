{
    "name": "Approval Request: Current Fiscal Year Exception",
    "version": "16.0.1.0.0",
    "summary": """ Block submitting an approval request unless its ปีงบประมาณ is the current one """,
    "category": "Accounting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "agx_approval",
    ],
    "data": [
        "data/exception_rule_data.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "auto_install": False,
    "application": False,
    "license": "AGPL-3",
}
