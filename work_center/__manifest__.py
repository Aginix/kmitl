{
    "name": "Work Center",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Productivity",
    "summary": "ศูนย์งาน: stamp documents with the unit that owns and tracks them, "
    "with a per-area overview of configurable counters",
    "depends": [
        "mail",
        "operating_unit",
    ],
    "data": [
        "security/work_center_security.xml",
        "security/ir.model.access.csv",
        "views/work_center_views.xml",
        "views/work_center_rule_views.xml",
        "views/work_center_counter_views.xml",
        "views/work_center_area_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
