{
    "name": "KMITL Budget Transfer — Buddy Verification",
    "version": "16.0.1.0.0",
    "summary": """ The unit's Buddy verifies a confirmed budget transfer """
    """ before it is sent for approval """,
    "category": "KMITL/Budgeting",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "depends": [
        "budget_transfer",
        "budget_buddy",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_activity_type_data.xml",
        "wizard/budget_transfer_verify_return_wizard_views.xml",
        "views/budget_transfer_views.xml",
    ],
    "application": False,
    "license": "AGPL-3",
}
