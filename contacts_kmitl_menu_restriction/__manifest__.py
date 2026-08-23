{
    "name": "Contacts KMITL Menu Restriction",
    "version": "16.0.1.0.0",
    "summary": "Restrict Contacts app visibility to can_access_contacts_app group",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "contacts_kmitl",
    ],
    "data": [
        "security/contacts_security.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
