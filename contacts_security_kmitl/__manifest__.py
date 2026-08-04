{
    "name": "Contacts Security KMITL",
    "version": "16.0.1.0.0",
    "summary": "Restrict Contacts app visibility to purchase and billing users",
    "category": "KMITL",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "contacts_kmitl",
        "purchase",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/menu.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
