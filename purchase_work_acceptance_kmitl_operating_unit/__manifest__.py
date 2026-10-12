{
    "name": "Purchase Work Acceptance Committee Access across OUs",
    "version": "16.0.1.0.0",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "summary": "Let an assigned WA committee member open the WA they must "
    "inspect even when their user is not attached to the WA's OU.",
    "depends": [
        "purchase_work_acceptance_operating_unit_access_all",
        "purchase_work_acceptance_kmitl",
    ],
    "data": ["security/security.xml"],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
