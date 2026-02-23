# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Advance Payment",
    "version": "16.0.1.0.0",
    "category": "Advance Payment",
    "license": "LGPL-3",
    "author": "KMITL",
    "depends": [
        "hr",
        "account",
        "mail",
    ],
    "data": [
        "data/sequence.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/advance_payment_type_views.xml",
        "views/advance_payment_views.xml",
        "views/advance_payment_menus.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": True,
}
