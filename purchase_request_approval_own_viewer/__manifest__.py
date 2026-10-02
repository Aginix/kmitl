{
    "name": "Purchase Request Approval: Own Viewer",
    "version": "16.0.1.0.0",
    "summary": "Let every internal user read purchase.request.approval where they are the requester",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchases",
    "depends": ["purchase_request_approval"],
    "data": [
        "views/purchase_request_approval_menus.xml",
        "views/purchase_request_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
