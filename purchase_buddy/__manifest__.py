{
    "name": "KMITL Purchase Buddy",
    "version": "16.0.1.0.0",
    "summary": """ Central procurement buddies (เจ้าหน้าที่ Buddy พัสดุ) """
    """ and the units they cover """,
    "category": "KMITL/Purchase",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "purchase_request",
    ],
    "data": [
        "security/purchase_buddy_security.xml",
        "security/ir.model.access.csv",
        "views/purchase_buddy_views.xml",
    ],
    "application": False,
    "license": "AGPL-3",
}
