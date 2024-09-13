# © 2015-17 ForgeFlow S.L.
# - Jordi Ballester Alomar
# © 2015-17 Serpent Consulting Services Pvt. Ltd. - Sudhir Arya
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Operating Unit in Purchase Orders",
    "summary": "Adds the concecpt of operating unit (OU) in purchase order "
    "management",
    "version": "16.0.1.0.0",
    "author": "nopparuts, " "Aginix Technologies," "Odoo Community Association (OCA)",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase Management",
    "depends": ["purchase", "account_operating_unit"],
    "license": "LGPL-3",
    "data": [
        "security/purchase_security.xml",
        "report/purchase_report_view.xml",
        "views/purchase_order_view.xml",
        "views/purchase_order_line_view.xml",
        "views/account_move_view.xml",
    ],
    "demo": ["demo/purchase_order_demo.xml"],
    "installable": True,
}
