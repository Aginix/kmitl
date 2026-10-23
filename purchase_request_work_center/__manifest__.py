{
    "name": "Purchase Request Work Center",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase Management",
    "summary": "Route พ.1 to a work center and add the งานพัสดุ overview",
    "depends": [
        "work_center",
        # Every พ.1 state referenced by the counters must exist; this module
        # loads last in the purchase.request state chain.
        "purchase_request_approval",
        "purchase_request_operating_unit",
    ],
    "data": [
        "data/work_center_data.xml",
        "views/purchase_request_views.xml",
        "views/work_center_menus.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
