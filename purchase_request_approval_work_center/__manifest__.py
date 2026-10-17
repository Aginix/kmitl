{
    "name": "Purchase Request Approval Work Center",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Purchase Management",
    "summary": "Route พจ.1 to a ศูนย์งาน of the งานพัสดุ area",
    "depends": [
        "purchase_request_work_center",
        "purchase_request_approval_operating_unit",
    ],
    "data": [
        "data/work_center_data.xml",
        "views/purchase_request_approval_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
