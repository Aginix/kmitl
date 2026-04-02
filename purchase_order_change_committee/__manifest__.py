{
    "name": "Purchase Order Change Committee",
    "version": "16.0.1.0.0",
    "summary": "Allow editing committee members on PO via change tracking",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_order_change",
        "purchase_order_procurement_committee",
        "purchase_work_acceptance_kmitl",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/purchase_change_section_data.xml",
        "wizards/purchase_order_change_wizard.xml",
        "views/purchase_order_change_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
