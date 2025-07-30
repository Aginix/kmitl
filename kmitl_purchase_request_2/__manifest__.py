{
    "name": "Kmitl_purchase_request_2",
    "version": "16.0.1.0.0",
    "summary": """ Kmitl_purchase_request_2 Summary """,
    "depends": ["base", "web", "kmitl_purchase_request", "purchase_invoice_plan"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_attachment_views.xml",
        "views/purchase_order_bidder_line_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_views.xml",
        "views/rfq_wizard_inherit_views.xml"
    ],
    "assets": {
        "web.assets_backend": ["kmitl_purchase_request_2/static/src/**/*"],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
