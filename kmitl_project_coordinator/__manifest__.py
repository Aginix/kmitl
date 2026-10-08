{
    "name": "KMITL Project — Coordinator",
    "summary": "ผู้ประสานงานโครงการ: Own Project access, cross-OU visibility "
    "and status notifications for the project's owners",
    "version": "16.0.1.0.0",
    "category": "Project",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "license": "LGPL-3",
    "depends": ["kmitl_project"],
    "data": [
        "data/mail_message_subtype_data.xml",
        "security/security.xml",
        "views/kmitl_project_views.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": False,
}
