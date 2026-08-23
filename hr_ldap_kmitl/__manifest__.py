{
    "name": "HR LDAP User Provisioning (KMITL)",
    "version": "16.0.1.0.0",
    "category": "Human Resources",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "summary": "Auto-link users created via LDAP to their existing employee "
    "record by work email.",
    "depends": ["hr", "base_automation"],
    "data": [
        "data/base_automation.xml",
        "data/backfill_server_action.xml",
    ],
    "auto_install": False,
    "application": False,
    "license": "AGPL-3",
}
