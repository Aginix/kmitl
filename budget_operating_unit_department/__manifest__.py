{
    "name": "Budget Operating Unit Department",
    "version": "16.0.1.0.0",
    "summary": "A budget transfer line is visible to the OU of its own department",
    "author": "Aginix Technologies",
    "website": "https://github.com/Aginix/kmitl",
    "category": "KMITL/Budgeting",
    "depends": ["analytic_operating_unit", "budget_operating_unit_access_all"],
    "data": ["security/budget_security.xml"],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
