{
    "name": "Purchase Order Change Installment",
    "version": "16.0.1.0.0",
    "summary": "Allow editing work acceptance installments on PO via change tracking",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "KMITL",
    "depends": [
        "purchase_order_change",
        "purchase_invoice_plan_kmitl",
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
